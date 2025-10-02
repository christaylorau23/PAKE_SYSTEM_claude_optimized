/**
 * PAKE System - Video Job Processor
 * Single Responsibility: Job queue management and processing for video generation
 */

import { VideoProcessingJob, JobPriority, VideoStatus } from '../types';

export interface VideoJobProcessor {
  addJob(job: VideoProcessingJob): void;
  processJobs(): Promise<void>;
  getJobStatus(jobId: string): VideoProcessingJob | undefined;
  cancelJob(jobId: string): boolean;
  getQueueStats(): QueueStats;
}

export interface QueueStats {
  totalJobs: number;
  pendingJobs: number;
  processingJobs: number;
  completedJobs: number;
  failedJobs: number;
  averageProcessingTime: number;
}

export class VideoJobProcessorImpl implements VideoJobProcessor {
  private jobQueue: Map<string, VideoProcessingJob> = new Map();
  private processing = false;
  private logger: any;
  private maxConcurrentJobs: number;

  constructor(logger: any, maxConcurrentJobs: number = 5) {
    this.logger = logger;
    this.maxConcurrentJobs = maxConcurrentJobs;
  }

  addJob(job: VideoProcessingJob): void {
    this.jobQueue.set(job.id, job);
    this.logger.info('Job added to queue', { jobId: job.id, priority: job.priority });
    
    // Start processing if not already running
    if (!this.processing) {
      this.processJobs();
    }
  }

  async processJobs(): Promise<void> {
    if (this.processing) return;
    
    this.processing = true;
    this.logger.info('Starting job processing');

    try {
      while (this.jobQueue.size > 0) {
        const jobs = Array.from(this.jobQueue.values())
          .filter(job => job.status === VideoStatus.PENDING)
          .sort((a, b) => b.priority - a.priority)
          .slice(0, this.maxConcurrentJobs);

        if (jobs.length === 0) break;

        // Process jobs concurrently
        await Promise.allSettled(
          jobs.map(job => this.processJob(job))
        );
      }
    } finally {
      this.processing = false;
      this.logger.info('Job processing completed');
    }
  }

  private async processJob(job: VideoProcessingJob): Promise<void> {
    try {
      job.status = VideoStatus.IN_PROGRESS;
      job.updatedAt = new Date();
      
      this.logger.info('Processing job', { jobId: job.id });
      
      // Simulate job processing - would integrate with actual video generation
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      job.status = VideoStatus.COMPLETED;
      job.updatedAt = new Date();
      
      this.logger.info('Job completed', { jobId: job.id });
    } catch (error) {
      job.status = VideoStatus.FAILED;
      job.updatedAt = new Date();
      job.attempts++;
      
      this.logger.error('Job failed', { jobId: job.id, error: error.message });
      
      // Retry logic
      if (job.attempts < job.maxAttempts) {
        job.status = VideoStatus.PENDING;
        this.logger.info('Job queued for retry', { jobId: job.id, attempts: job.attempts });
      }
    }
  }

  getJobStatus(jobId: string): VideoProcessingJob | undefined {
    return this.jobQueue.get(jobId);
  }

  cancelJob(jobId: string): boolean {
    const job = this.jobQueue.get(jobId);
    if (job && job.status === VideoStatus.PENDING) {
      job.status = VideoStatus.FAILED;
      this.jobQueue.delete(jobId);
      this.logger.info('Job cancelled', { jobId });
      return true;
    }
    return false;
  }

  getQueueStats(): QueueStats {
    const jobs = Array.from(this.jobQueue.values());
    const completedJobs = jobs.filter(job => job.status === VideoStatus.COMPLETED);
    const processingJobs = jobs.filter(job => job.status === VideoStatus.IN_PROGRESS);
    const pendingJobs = jobs.filter(job => job.status === VideoStatus.PENDING);
    const failedJobs = jobs.filter(job => job.status === VideoStatus.FAILED);

    const averageProcessingTime = completedJobs.length > 0
      ? completedJobs.reduce((sum, job) => {
          const duration = job.updatedAt.getTime() - job.createdAt.getTime();
          return sum + duration;
        }, 0) / completedJobs.length
      : 0;

    return {
      totalJobs: jobs.length,
      pendingJobs: pendingJobs.length,
      processingJobs: processingJobs.length,
      completedJobs: completedJobs.length,
      failedJobs: failedJobs.length,
      averageProcessingTime
    };
  }
}
