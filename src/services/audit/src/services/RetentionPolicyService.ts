/**
 * Data Retention Policy Service
 * Manages automated data retention policies and archival scheduling
 */

import cron from 'node-cron';
import { v4 as uuidv4 } from 'uuid';
import {
  RetentionPolicy,
  RetentionCriteria,
  ArchivalJob,
  ArchivalJobStatus,
  ArchivalType,
  AuditEvent,
  ActionType,
  ActorType,
  ActionResult,
} from '../types/audit.types';
import { AuditStorageService } from './AuditStorageService';
import { Logger } from '../utils/logger';

interface PolicyEvaluation {
  policyId: string;
  eventsAffected: number;
  archivalType: ArchivalType;
  estimatedSize: number;
  estimatedCost: number;
}

export class RetentionPolicyService {
  private readonly logger = new Logger('RetentionPolicyService');
  private readonly storageService: AuditStorageService;
  private readonly policies: Map<string, RetentionPolicy> = new Map();
  private readonly scheduledJobs: Map<string, cron.ScheduledTask> = new Map();
  private readonly activeJobs: Map<string, ArchivalJob> = new Map();

  constructor(storageService: AuditStorageService) {
    this.storageService = storageService;
  }

  /**
   * Initialize retention policy service with default policies
   */
  async initialize(): Promise<void> {
    try {
      // Load existing policies from storage
      await this.loadPoliciesFromStorage();

      // Create default policies if none exist
      if (this.policies.size === 0) {
        await this.createDefaultPolicies();
      }

      // Schedule policy enforcement
      this.scheduleAllPolicies();

      this.logger.info('Retention policy service initialized', {
        policyCount: this.policies.size,
      });
    } catch (error) {
      this.logger.error('Failed to initialize retention policy service', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Create a new retention policy
   */
  async createPolicy(
    policy: Omit<RetentionPolicy, 'id' | 'createdAt' | 'updatedAt'>
  ): Promise<RetentionPolicy> {
    const newPolicy: RetentionPolicy = {
      ...policy,
      id: uuidv4(),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    // Validate policy
    this.validatePolicy(newPolicy);

    // Store policy
    this.policies.set(newPolicy.id, newPolicy);
    await this.savePolicyToStorage(newPolicy);

    // Schedule if enabled
    if (newPolicy.enabled) {
      this.schedulePolicy(newPolicy);
    }

    this.logger.info('Retention policy created', { policyId: newPolicy.id });
    return newPolicy;
  }

  /**
   * Update existing retention policy
   */
  async updatePolicy(
    policyId: string,
    updates: Partial<RetentionPolicy>
  ): Promise<RetentionPolicy> {
    const existingPolicy = this.policies.get(policyId);

    if (!existingPolicy) {
      throw new Error(`Retention policy ${policyId} not found`);
    }

    const updatedPolicy: RetentionPolicy = {
      ...existingPolicy,
      ...updates,
      id: policyId, // Ensure ID cannot be changed
      updatedAt: new Date().toISOString(),
    };

    // Validate updated policy
    this.validatePolicy(updatedPolicy);

    // Update in memory and storage
    this.policies.set(policyId, updatedPolicy);
    await this.savePolicyToStorage(updatedPolicy);

    // Reschedule if needed
    this.unschedulePolicy(policyId);
    if (updatedPolicy.enabled) {
      this.schedulePolicy(updatedPolicy);
    }

    this.logger.info('Retention policy updated', { policyId });
    return updatedPolicy;
  }

  /**
   * Delete retention policy
   */
  async deletePolicy(policyId: string): Promise<void> {
    const policy = this.policies.get(policyId);

    if (!policy) {
      throw new Error(`Retention policy ${policyId} not found`);
    }

    // Unschedule and remove
    this.unschedulePolicy(policyId);
    this.policies.delete(policyId);
    await this.deletePolicyFromStorage(policyId);

    this.logger.info('Retention policy deleted', { policyId });
  }

  /**
   * Get all retention policies
   */
  getAllPolicies(): RetentionPolicy[] {
    return Array.from(this.policies.values());
  }

  /**
   * Get specific retention policy
   */
  getPolicy(policyId: string): RetentionPolicy | null {
    return this.policies.get(policyId) || null;
  }

  /**
   * Evaluate policy impact before applying
   */
  async evaluatePolicy(policy: RetentionPolicy): Promise<PolicyEvaluation> {
    const cutoffDate = this.calculateCutoffDate(policy);
    const eventsQuery = this.buildQueryFromCriteria(
      policy.criteria,
      cutoffDate
    );

    // Get count and size estimates
    const events = await this.storageService.queryEvents(eventsQuery);
    const eventsAffected = events.length;
    const estimatedSize = this.estimateDataSize(events);

    // Determine archival type based on age
    const archivalType = this.determineArchivalType(policy, cutoffDate);
    const estimatedCost = this.estimateStorageCost(estimatedSize, archivalType);

    return {
      policyId: policy.id,
      eventsAffected,
      archivalType,
      estimatedSize,
      estimatedCost,
    };
  }

  /**
   * Manually trigger policy execution
   */
  async executePolicy(policyId: string): Promise<ArchivalJob> {
    const policy = this.policies.get(policyId);

    if (!policy) {
      throw new Error(`Retention policy ${policyId} not found`);
    }

    if (!policy.enabled) {
      throw new Error(`Retention policy ${policyId} is disabled`);
    }

    return this.executePolicyInternal(policy);
  }

  /**
   * Get active archival jobs
   */
  getActiveJobs(): ArchivalJob[] {
    return Array.from(this.activeJobs.values());
  }

  /**
   * Get job status
   */
  getJobStatus(jobId: string): ArchivalJob | null {
    return this.activeJobs.get(jobId) || null;
  }

  /**
   * Cancel active job
   */
  async cancelJob(jobId: string): Promise<void> {
    const job = this.activeJobs.get(jobId);

    if (!job) {
      throw new Error(`Job ${jobId} not found`);
    }

    if (job.status !== ArchivalJobStatus.RUNNING) {
      throw new Error(`Job ${jobId} is not running`);
    }

    job.status = ArchivalJobStatus.CANCELLED;
    job.completedAt = new Date().toISOString();

    this.activeJobs.set(jobId, job);
    await this.storageService.updateArchivalJob(job);

    this.logger.info('Archival job cancelled', { jobId });
  }

  /**
   * Create default retention policies
   */
  private async createDefaultPolicies(): Promise<void> {
    const defaultPolicies: Omit<
      RetentionPolicy,
      'id' | 'createdAt' | 'updatedAt'
    >[] = [
      {
        name: 'Standard Hot Storage',
        description: 'Move general audit events to warm storage after 30 days',
        criteria: {
          criticalOnly: false,
        },
        hotStorageDays: 30,
        warmStorageDays: 90,
        coldStorageYears: 7,
        enabled: true,
      },
      {
        name: 'Critical Events Extended',
        description: 'Keep critical security events in hot storage for 90 days',
        criteria: {
          actionTypes: [ActionType.ACCESS_DENIED, ActionType.LOGIN],
          results: [ActionResult.FAILURE, ActionResult.DENIED],
          criticalOnly: true,
        },
        hotStorageDays: 90,
        warmStorageDays: 180,
        coldStorageYears: 10,
        enabled: true,
      },
      {
        name: 'System Events Minimal',
        description: 'Archive system events quickly to reduce storage costs',
        criteria: {
          actorTypes: [ActorType.SYSTEM],
          actionTypes: [ActionType.CREATE, ActionType.UPDATE],
        },
        hotStorageDays: 7,
        warmStorageDays: 30,
        coldStorageYears: 3,
        enabled: true,
      },
      {
        name: 'User Activity Standard',
        description: 'Standard retention for user activity events',
        criteria: {
          actorTypes: [ActorType.USER],
          resourceTypes: ['vault', 'note', 'knowledge'],
        },
        hotStorageDays: 60,
        warmStorageDays: 365,
        coldStorageYears: 7,
        enabled: true,
      },
    ];

    for (const policy of defaultPolicies) {
      await this.createPolicy(policy);
    }

    this.logger.info('Default retention policies created', {
      count: defaultPolicies.length,
    });
  }

  /**
   * Schedule all enabled policies
   */
  private scheduleAllPolicies(): void {
    for (const policy of this.policies.values()) {
      if (policy.enabled) {
        this.schedulePolicy(policy);
      }
    }
  }

  /**
   * Schedule individual policy
   */
  private schedulePolicy(policy: RetentionPolicy): void {
    // Schedule daily at 2 AM
    const cronExpression = '0 2 * * *';

    const task = cron.schedule(
      cronExpression,
      async () => {
        try {
          this.logger.info('Executing scheduled retention policy', {
            policyId: policy.id,
          });
          await this.executePolicyInternal(policy);
        } catch (error) {
          this.logger.error('Scheduled policy execution failed', {
            policyId: policy.id,
            error: error.message,
          });
        }
      },
      {
        scheduled: false, // Don't start immediately
      }
    );

    this.scheduledJobs.set(policy.id, task);
    task.start();

    this.logger.debug('Policy scheduled', { policyId: policy.id });
  }

  /**
   * Unschedule policy
   */
  private unschedulePolicy(policyId: string): void {
    const task = this.scheduledJobs.get(policyId);

    if (task) {
      task.stop();
      this.scheduledJobs.delete(policyId);
      this.logger.debug('Policy unscheduled', { policyId });
    }
  }

  /**
   * Execute policy internally
   */
  private async executePolicyInternal(
    policy: RetentionPolicy
  ): Promise<ArchivalJob> {
    const cutoffDate = this.calculateCutoffDate(policy);
    const archivalType = this.determineArchivalType(policy, cutoffDate);

    const job: ArchivalJob = {
      id: uuidv4(),
      status: ArchivalJobStatus.PENDING,
      type: archivalType,
      criteria: {
        olderThan: cutoffDate.toISOString(),
        resourceTypes: policy.criteria.resourceTypes,
      },
      progress: {
        total: 0,
        processed: 0,
        errors: 0,
      },
      startedAt: new Date().toISOString(),
    };

    try {
      // Store job
      this.activeJobs.set(job.id, job);
      await this.storageService.updateArchivalJob(job);

      // Start execution
      job.status = ArchivalJobStatus.RUNNING;
      await this.storageService.updateArchivalJob(job);

      // Execute archival
      await this.storageService.createArchivalJob(
        archivalType,
        cutoffDate,
        policy.criteria
      );

      // Mark as completed
      job.status = ArchivalJobStatus.COMPLETED;
      job.completedAt = new Date().toISOString();

      this.activeJobs.set(job.id, job);
      await this.storageService.updateArchivalJob(job);

      this.logger.info('Retention policy executed successfully', {
        policyId: policy.id,
        jobId: job.id,
        archivalType: archivalType,
      });

      return job;
    } catch (error) {
      job.status = ArchivalJobStatus.FAILED;
      job.error = error.message;
      job.completedAt = new Date().toISOString();

      this.activeJobs.set(job.id, job);
      await this.storageService.updateArchivalJob(job);

      this.logger.error('Retention policy execution failed', {
        policyId: policy.id,
        jobId: job.id,
        error: error.message,
      });

      throw error;
    }
  }

  /**
   * Calculate cutoff date based on policy
   */
  private calculateCutoffDate(policy: RetentionPolicy): Date {
    const now = new Date();
    const cutoffDate = new Date(now);
    cutoffDate.setDate(now.getDate() - policy.hotStorageDays);
    return cutoffDate;
  }

  /**
   * Determine archival type based on policy and age
   */
  private determineArchivalType(
    policy: RetentionPolicy,
    cutoffDate: Date
  ): ArchivalType {
    const now = new Date();
    const daysSinceCutoff = Math.floor(
      (now.getTime() - cutoffDate.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (daysSinceCutoff <= policy.warmStorageDays) {
      return ArchivalType.HOT_TO_WARM;
    } else if (daysSinceCutoff <= policy.coldStorageYears * 365) {
      return ArchivalType.WARM_TO_COLD;
    } else {
      return ArchivalType.PERMANENT_DELETE;
    }
  }

  /**
   * Build query from retention criteria
   */
  private buildQueryFromCriteria(
    criteria: RetentionCriteria,
    cutoffDate: Date
  ): any {
    const query: any = {
      endTime: cutoffDate,
      limit: 10000,
    };

    if (criteria.resourceTypes) {
      query.resourceTypes = criteria.resourceTypes;
    }

    if (criteria.actionTypes) {
      query.actionTypes = criteria.actionTypes;
    }

    if (criteria.actorTypes) {
      query.actorTypes = criteria.actorTypes;
    }

    if (criteria.results) {
      query.results = criteria.results;
    }

    return query;
  }

  /**
   * Estimate data size
   */
  private estimateDataSize(events: AuditEvent[]): number {
    if (events.length === 0) return 0;

    const sampleSize = Math.min(100, events.length);
    const sampleEvents = events.slice(0, sampleSize);
    const avgSize =
      sampleEvents.reduce(
        (sum, event) => sum + JSON.stringify(event).length,
        0
      ) / sampleSize;

    return Math.ceil(avgSize * events.length);
  }

  /**
   * Estimate storage cost
   */
  private estimateStorageCost(
    sizeBytes: number,
    archivalType: ArchivalType
  ): number {
    const sizeGB = sizeBytes / (1024 * 1024 * 1024);

    // Rough AWS pricing estimates (USD per GB per month)
    const pricing = {
      [ArchivalType.HOT_TO_WARM]: 0.0125, // S3 Standard-IA
      [ArchivalType.WARM_TO_COLD]: 0.004, // S3 Glacier
      [ArchivalType.PERMANENT_DELETE]: 0, // No cost for deletion
    };

    return sizeGB * (pricing[archivalType] || 0);
  }

  /**
   * Validate retention policy
   */
  private validatePolicy(policy: RetentionPolicy): void {
    if (!policy.name || policy.name.trim().length === 0) {
      throw new Error('Policy name is required');
    }

    if (policy.hotStorageDays < 0) {
      throw new Error('Hot storage days must be non-negative');
    }

    if (policy.warmStorageDays < policy.hotStorageDays) {
      throw new Error(
        'Warm storage days must be greater than or equal to hot storage days'
      );
    }

    if (policy.coldStorageYears < 0) {
      throw new Error('Cold storage years must be non-negative');
    }
  }

  /**
   * Load policies from storage (placeholder implementation)
   */
  private async loadPoliciesFromStorage(): Promise<void> {
    // In a real implementation, this would load from database
    this.logger.debug('Loading retention policies from storage');
  }

  /**
   * Save policy to storage (placeholder implementation)
   */
  private async savePolicyToStorage(policy: RetentionPolicy): Promise<void> {
    // In a real implementation, this would save to database
    this.logger.debug('Saving retention policy to storage', {
      policyId: policy.id,
    });
  }

  /**
   * Delete policy from storage (placeholder implementation)
   */
  private async deletePolicyFromStorage(policyId: string): Promise<void> {
    // In a real implementation, this would delete from database
    this.logger.debug('Deleting retention policy from storage', { policyId });
  }

  /**
   * Close service and cleanup
   */
  async close(): Promise<void> {
    // Stop all scheduled jobs
    for (const task of this.scheduledJobs.values()) {
      task.stop();
    }
    this.scheduledJobs.clear();

    this.logger.info('Retention policy service closed');
  }
}
