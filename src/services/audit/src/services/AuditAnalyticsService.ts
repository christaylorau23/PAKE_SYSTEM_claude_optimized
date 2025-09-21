/**
 * Audit Analytics and Anomaly Detection Service
 * Provides advanced analytics and suspicious pattern detection for audit events
 */

import {
  AuditEvent,
  AuditAnalytics,
  AuditAlert,
  AlertType,
  AlertSeverity,
  ActionType,
  ActionResult,
  ActorType,
} from '../types/audit.types';
import { AuditStorageService } from './AuditStorageService';
import { Logger } from '../utils/logger';

interface PatternDetectionRule {
  id: string;
  name: string;
  description: string;
  type: AlertType;
  severity: AlertSeverity;
  enabled: boolean;
  timeWindow: number; // minutes
  threshold: number;
  conditions: PatternCondition[];
  actions: string[]; // Actions to take when triggered
}

interface PatternCondition {
  field: string;
  operator: 'equals' | 'contains' | 'greater_than' | 'less_than' | 'in';
  value: any;
  weight?: number; // For scoring
}

interface AnomalyScore {
  eventId: string;
  score: number; // 0-100, higher = more suspicious
  reasons: string[];
  timestamp: string;
}

interface UserBehaviorProfile {
  userId: string;
  normalHours: number[]; // Active hours (0-23)
  commonResources: string[];
  commonActions: ActionType[];
  averageSessionDuration: number;
  typicalIPRanges: string[];
  lastUpdated: string;
}

interface SystemMetrics {
  hourlyEventVolume: number[];
  errorRateByHour: number[];
  topFailedActions: Array<{ action: string; count: number }>;
  topFailedResources: Array<{ resource: string; count: number }>;
  unusualActivityPeaks: Array<{
    hour: number;
    volume: number;
    deviation: number;
  }>;
}

export class AuditAnalyticsService {
  private readonly logger = new Logger('AuditAnalyticsService');
  private readonly storageService: AuditStorageService;
  private readonly detectionRules: Map<string, PatternDetectionRule> =
    new Map();
  private readonly userProfiles: Map<string, UserBehaviorProfile> = new Map();
  private readonly recentAlerts: Map<string, AuditAlert> = new Map();

  // Anomaly detection thresholds
  private readonly ANOMALY_THRESHOLDS = {
    HIGH_ERROR_RATE: 0.1, // 10%
    UNUSUAL_HOUR_ACTIVITY: 3.0, // 3 standard deviations
    RAPID_FAILED_ATTEMPTS: 5, // attempts per minute
    BULK_DATA_ACCESS: 100, // records per minute
    GEOGRAPHIC_ANOMALY: 1000, // km distance
    NEW_USER_AGENT: true,
    PRIVILEGE_ESCALATION: true,
  };

  constructor(storageService: AuditStorageService) {
    this.storageService = storageService;
  }

  /**
   * Initialize analytics service with default detection rules
   */
  async initialize(): Promise<void> {
    try {
      await this.loadDetectionRules();
      await this.loadUserProfiles();

      // Start background processes
      this.scheduleAnalytics();

      this.logger.info('Audit analytics service initialized', {
        rulesCount: this.detectionRules.size,
        profilesCount: this.userProfiles.size,
      });
    } catch (error) {
      this.logger.error('Failed to initialize analytics service', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Analyze single event for anomalies
   */
  async analyzeEvent(event: AuditEvent): Promise<AnomalyScore> {
    const score = await this.calculateAnomalyScore(event);

    // Trigger alerts if score is high
    if (score.score > 70) {
      await this.createAlert(event, score);
    }

    return score;
  }

  /**
   * Analyze batch of events
   */
  async analyzeBatch(events: AuditEvent[]): Promise<AnomalyScore[]> {
    const scores: AnomalyScore[] = [];

    for (const event of events) {
      const score = await this.analyzeEvent(event);
      scores.push(score);
    }

    // Look for batch patterns
    await this.detectBatchPatterns(events, scores);

    return scores;
  }

  /**
   * Generate comprehensive analytics report
   */
  async generateAnalytics(
    startDate: Date,
    endDate: Date
  ): Promise<AuditAnalytics> {
    try {
      const events = await this.storageService.queryEvents({
        startTime: startDate,
        endTime: endDate,
        limit: 100000,
      });

      const metrics = this.calculateMetrics(events, startDate, endDate);
      const trends = this.calculateTrends(events, startDate, endDate);
      const anomalies = await this.detectAnomalies(events);

      return {
        period: {
          start: startDate.toISOString(),
          end: endDate.toISOString(),
        },
        metrics,
        trends,
        anomalies: anomalies.map(score => ({
          type: 'behavioral_anomaly',
          description: score.reasons.join(', '),
          severity: this.scoreToSeverity(score.score),
          detectedAt: score.timestamp,
        })),
      };
    } catch (error) {
      this.logger.error('Failed to generate analytics', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Detect suspicious patterns in real-time
   */
  async detectSuspiciousPatterns(events: AuditEvent[]): Promise<AuditAlert[]> {
    const alerts: AuditAlert[] = [];

    for (const rule of this.detectionRules.values()) {
      if (!rule.enabled) continue;

      const matchingEvents = this.filterEventsByRule(events, rule);

      if (matchingEvents.length >= rule.threshold) {
        const alert = await this.createPatternAlert(rule, matchingEvents);
        alerts.push(alert);
      }
    }

    return alerts;
  }

  /**
   * Update user behavior profile
   */
  async updateUserProfile(userId: string, events: AuditEvent[]): Promise<void> {
    const userEvents = events.filter(
      e => e.actor.id === userId && e.actor.type === ActorType.USER
    );

    if (userEvents.length === 0) return;

    let profile = this.userProfiles.get(userId);

    if (!profile) {
      profile = {
        userId,
        normalHours: [],
        commonResources: [],
        commonActions: [],
        averageSessionDuration: 0,
        typicalIPRanges: [],
        lastUpdated: new Date().toISOString(),
      };
    }

    // Update profile with new events
    profile.normalHours = this.calculateNormalHours(userEvents);
    profile.commonResources = this.calculateCommonResources(userEvents);
    profile.commonActions = this.calculateCommonActions(userEvents);
    profile.typicalIPRanges = this.calculateTypicalIPRanges(userEvents);
    profile.lastUpdated = new Date().toISOString();

    this.userProfiles.set(userId, profile);

    this.logger.debug('User profile updated', {
      userId,
      eventCount: userEvents.length,
    });
  }

  /**
   * Get active alerts
   */
  getActiveAlerts(): AuditAlert[] {
    return Array.from(this.recentAlerts.values())
      .filter(alert => !alert.resolved)
      .sort(
        (a, b) =>
          new Date(b.triggeredAt).getTime() - new Date(a.triggeredAt).getTime()
      );
  }

  /**
   * Acknowledge alert
   */
  async acknowledgeAlert(
    alertId: string,
    acknowledgedBy: string
  ): Promise<void> {
    const alert = this.recentAlerts.get(alertId);

    if (!alert) {
      throw new Error(`Alert ${alertId} not found`);
    }

    alert.acknowledged = true;
    alert.acknowledgedBy = acknowledgedBy;
    alert.acknowledgedAt = new Date().toISOString();

    this.recentAlerts.set(alertId, alert);

    this.logger.info('Alert acknowledged', { alertId, acknowledgedBy });
  }

  /**
   * Resolve alert
   */
  async resolveAlert(alertId: string): Promise<void> {
    const alert = this.recentAlerts.get(alertId);

    if (!alert) {
      throw new Error(`Alert ${alertId} not found`);
    }

    alert.resolved = true;
    alert.resolvedAt = new Date().toISOString();

    this.recentAlerts.set(alertId, alert);

    this.logger.info('Alert resolved', { alertId });
  }

  /**
   * Calculate anomaly score for event
   */
  private async calculateAnomalyScore(
    event: AuditEvent
  ): Promise<AnomalyScore> {
    const reasons: string[] = [];
    let score = 0;

    // Check for failed actions
    if (
      event.action.result === ActionResult.FAILURE ||
      event.action.result === ActionResult.DENIED
    ) {
      score += 20;
      reasons.push('Failed action attempt');
    }

    // Check for unusual time patterns
    const eventHour = new Date(event.timestamp).getHours();
    if (await this.isUnusualHour(event.actor.id, eventHour)) {
      score += 15;
      reasons.push('Activity outside normal hours');
    }

    // Check for user behavior anomalies
    if (event.actor.type === ActorType.USER) {
      const profile = this.userProfiles.get(event.actor.id);
      if (profile) {
        if (!profile.commonResources.includes(event.action.resource)) {
          score += 10;
          reasons.push('Access to uncommon resource');
        }

        if (!profile.commonActions.includes(event.action.type)) {
          score += 5;
          reasons.push('Unusual action type for user');
        }

        if (
          event.actor.ip &&
          !this.isTypicalIP(event.actor.ip, profile.typicalIPRanges)
        ) {
          score += 25;
          reasons.push('Access from unusual IP address');
        }
      }
    }

    // Check for bulk operations
    if (await this.isBulkOperation(event)) {
      score += 15;
      reasons.push('Bulk operation detected');
    }

    // Check for privilege escalation
    if (this.isPrivilegeEscalation(event)) {
      score += 30;
      reasons.push('Potential privilege escalation');
    }

    // Administrative actions
    if (
      event.action.type === ActionType.CONFIGURE ||
      event.action.type === ActionType.DELETE
    ) {
      score += 10;
      reasons.push('Administrative action');
    }

    return {
      eventId: event.id,
      score: Math.min(score, 100),
      reasons,
      timestamp: event.timestamp,
    };
  }

  /**
   * Calculate analytics metrics
   */
  private calculateMetrics(
    events: AuditEvent[],
    startDate: Date,
    endDate: Date
  ): AuditAnalytics['metrics'] {
    const totalEvents = events.length;
    const hours = Math.max(
      1,
      (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60)
    );
    const eventsPerHour = new Array(24).fill(0);

    // Count events by hour
    events.forEach(event => {
      const hour = new Date(event.timestamp).getHours();
      eventsPerHour[hour]++;
    });

    // Calculate top actors, actions, resources
    const actorCounts = new Map<string, number>();
    const actionCounts = new Map<string, number>();
    const resourceCounts = new Map<string, number>();
    let errorCount = 0;
    let securityIncidents = 0;

    events.forEach(event => {
      // Count actors
      const actorKey = event.actor.id;
      actorCounts.set(actorKey, (actorCounts.get(actorKey) || 0) + 1);

      // Count actions
      const actionKey = event.action.type;
      actionCounts.set(actionKey, (actionCounts.get(actionKey) || 0) + 1);

      // Count resources
      const resourceKey = event.action.resource;
      resourceCounts.set(
        resourceKey,
        (resourceCounts.get(resourceKey) || 0) + 1
      );

      // Count errors
      if (
        event.action.result === ActionResult.ERROR ||
        event.action.result === ActionResult.FAILURE
      ) {
        errorCount++;
      }

      // Count security incidents
      if (
        event.action.result === ActionResult.DENIED ||
        event.action.type === ActionType.ACCESS_DENIED
      ) {
        securityIncidents++;
      }
    });

    return {
      totalEvents,
      eventsPerHour: eventsPerHour.map(
        count => count / Math.max(1, hours / 24)
      ),
      topActors: Array.from(actorCounts.entries())
        .map(([id, count]) => ({ id, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10),
      topActions: Array.from(actionCounts.entries())
        .map(([type, count]) => ({ type, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10),
      topResources: Array.from(resourceCounts.entries())
        .map(([resource, count]) => ({ resource, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10),
      errorRate: totalEvents > 0 ? (errorCount / totalEvents) * 100 : 0,
      securityIncidents,
    };
  }

  /**
   * Calculate trend data
   */
  private calculateTrends(
    events: AuditEvent[],
    startDate: Date,
    endDate: Date
  ): AuditAnalytics['trends'] {
    const dayMs = 1000 * 60 * 60 * 24;
    const days = Math.ceil((endDate.getTime() - startDate.getTime()) / dayMs);

    const dailyVolume = new Array(days).fill(0).map((_, i) => ({
      date: new Date(startDate.getTime() + i * dayMs)
        .toISOString()
        .split('T')[0],
      count: 0,
    }));

    const hourlyPattern = new Array(24)
      .fill(0)
      .map((_, hour) => ({ hour, count: 0 }));
    const userActivity = new Map<string, number>();

    events.forEach(event => {
      const eventDate = new Date(event.timestamp);
      const dayIndex = Math.floor(
        (eventDate.getTime() - startDate.getTime()) / dayMs
      );

      if (dayIndex >= 0 && dayIndex < days) {
        dailyVolume[dayIndex].count++;
      }

      hourlyPattern[eventDate.getHours()].count++;

      if (event.actor.type === ActorType.USER) {
        const current = userActivity.get(event.actor.id) || 0;
        userActivity.set(event.actor.id, current + 1);
      }
    });

    return {
      dailyVolume,
      hourlyPattern,
      userActivity: Array.from(userActivity.entries())
        .map(([userId, activityScore]) => ({ userId, activityScore }))
        .sort((a, b) => b.activityScore - a.activityScore)
        .slice(0, 20),
    };
  }

  /**
   * Detect anomalies in event batch
   */
  private async detectAnomalies(events: AuditEvent[]): Promise<AnomalyScore[]> {
    const anomalies: AnomalyScore[] = [];

    for (const event of events) {
      const score = await this.calculateAnomalyScore(event);
      if (score.score > 50) {
        anomalies.push(score);
      }
    }

    return anomalies.sort((a, b) => b.score - a.score);
  }

  /**
   * Create alert from anomaly
   */
  private async createAlert(
    event: AuditEvent,
    anomalyScore: AnomalyScore
  ): Promise<AuditAlert> {
    const alert: AuditAlert = {
      id: `alert-${event.id}`,
      type: AlertType.SUSPICIOUS_ACTIVITY,
      severity: this.scoreToSeverity(anomalyScore.score),
      title: `Suspicious activity detected`,
      description: `High anomaly score (${anomalyScore.score}) for event: ${anomalyScore.reasons.join(', ')}`,
      events: [event],
      triggeredAt: new Date().toISOString(),
      acknowledged: false,
      resolved: false,
    };

    this.recentAlerts.set(alert.id, alert);

    this.logger.warn('Security alert created', {
      alertId: alert.id,
      severity: alert.severity,
      score: anomalyScore.score,
      eventId: event.id,
    });

    return alert;
  }

  /**
   * Create alert from pattern detection
   */
  private async createPatternAlert(
    rule: PatternDetectionRule,
    events: AuditEvent[]
  ): Promise<AuditAlert> {
    const alert: AuditAlert = {
      id: `alert-pattern-${rule.id}-${Date.now()}`,
      type: rule.type,
      severity: rule.severity,
      title: `Pattern detected: ${rule.name}`,
      description: `${rule.description}. ${events.length} matching events in ${rule.timeWindow} minutes.`,
      events,
      triggeredAt: new Date().toISOString(),
      acknowledged: false,
      resolved: false,
    };

    this.recentAlerts.set(alert.id, alert);

    this.logger.warn('Pattern alert created', {
      alertId: alert.id,
      ruleId: rule.id,
      severity: alert.severity,
      eventCount: events.length,
    });

    return alert;
  }

  /**
   * Helper functions
   */
  private scoreToSeverity(score: number): AlertSeverity {
    if (score >= 90) return AlertSeverity.CRITICAL;
    if (score >= 70) return AlertSeverity.HIGH;
    if (score >= 50) return AlertSeverity.MEDIUM;
    return AlertSeverity.LOW;
  }

  private async isUnusualHour(userId: string, hour: number): Promise<boolean> {
    const profile = this.userProfiles.get(userId);
    if (!profile) return false;

    return !profile.normalHours.includes(hour);
  }

  private isTypicalIP(ip: string, ranges: string[]): boolean {
    // Simple IP range checking (implement proper CIDR matching)
    const ipParts = ip.split('.');
    const subnet = `${ipParts[0]}.${ipParts[1]}.${ipParts[2]}`;

    return ranges.some(range => range.startsWith(subnet));
  }

  private async isBulkOperation(event: AuditEvent): Promise<boolean> {
    // Check for bulk operations in metadata or rapid succession
    return (
      event.action.metadata?.batchSize > 10 ||
      event.action.metadata?.recordCount > 50
    );
  }

  private isPrivilegeEscalation(event: AuditEvent): boolean {
    const privilegeResources = [
      'user',
      'role',
      'permission',
      'admin',
      'config',
    ];
    return privilegeResources.some(resource =>
      event.action.resource.toLowerCase().includes(resource)
    );
  }

  private filterEventsByRule(
    events: AuditEvent[],
    rule: PatternDetectionRule
  ): AuditEvent[] {
    const cutoffTime = new Date(Date.now() - rule.timeWindow * 60 * 1000);

    return events.filter(event => {
      if (new Date(event.timestamp) < cutoffTime) return false;

      return rule.conditions.every(condition => {
        const fieldValue = this.getNestedValue(event, condition.field);
        return this.evaluateCondition(fieldValue, condition);
      });
    });
  }

  private getNestedValue(obj: any, path: string): any {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  }

  private evaluateCondition(
    fieldValue: any,
    condition: PatternCondition
  ): boolean {
    switch (condition.operator) {
      case 'equals':
        return fieldValue === condition.value;
      case 'contains':
        return String(fieldValue).includes(condition.value);
      case 'greater_than':
        return Number(fieldValue) > condition.value;
      case 'less_than':
        return Number(fieldValue) < condition.value;
      case 'in':
        return (
          Array.isArray(condition.value) && condition.value.includes(fieldValue)
        );
      default:
        return false;
    }
  }

  private calculateNormalHours(events: AuditEvent[]): number[] {
    const hourCounts = new Array(24).fill(0);
    events.forEach(event => {
      hourCounts[new Date(event.timestamp).getHours()]++;
    });

    const avgCount = hourCounts.reduce((sum, count) => sum + count, 0) / 24;
    return hourCounts
      .map((count, hour) => ({ hour, count }))
      .filter(({ count }) => count > avgCount * 0.5)
      .map(({ hour }) => hour);
  }

  private calculateCommonResources(events: AuditEvent[]): string[] {
    const resourceCounts = new Map<string, number>();
    events.forEach(event => {
      const count = resourceCounts.get(event.action.resource) || 0;
      resourceCounts.set(event.action.resource, count + 1);
    });

    return Array.from(resourceCounts.entries())
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([resource]) => resource);
  }

  private calculateCommonActions(events: AuditEvent[]): ActionType[] {
    const actionCounts = new Map<ActionType, number>();
    events.forEach(event => {
      const count = actionCounts.get(event.action.type) || 0;
      actionCounts.set(event.action.type, count + 1);
    });

    return Array.from(actionCounts.entries())
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([action]) => action);
  }

  private calculateTypicalIPRanges(events: AuditEvent[]): string[] {
    const ipCounts = new Map<string, number>();
    events.forEach(event => {
      if (event.actor.ip) {
        const subnet = event.actor.ip.split('.').slice(0, 3).join('.');
        const count = ipCounts.get(subnet) || 0;
        ipCounts.set(subnet, count + 1);
      }
    });

    return Array.from(ipCounts.keys()).slice(0, 5);
  }

  private async detectBatchPatterns(
    events: AuditEvent[],
    scores: AnomalyScore[]
  ): Promise<void> {
    // Look for patterns across the batch
    const highScoreEvents = scores.filter(score => score.score > 70);

    if (highScoreEvents.length > 5) {
      // Multiple high-score events might indicate coordinated attack
      const alert: AuditAlert = {
        id: `batch-alert-${Date.now()}`,
        type: AlertType.SYSTEM_COMPROMISE,
        severity: AlertSeverity.HIGH,
        title: 'Multiple suspicious activities detected',
        description: `${highScoreEvents.length} high-risk events detected in batch analysis`,
        events: events.filter(e =>
          highScoreEvents.some(s => s.eventId === e.id)
        ),
        triggeredAt: new Date().toISOString(),
        acknowledged: false,
        resolved: false,
      };

      this.recentAlerts.set(alert.id, alert);
    }
  }

  private scheduleAnalytics(): void {
    // Schedule periodic analytics tasks
    setInterval(async () => {
      try {
        await this.performHousekeeping();
      } catch (error) {
        this.logger.error('Analytics housekeeping failed', {
          error: error.message,
        });
      }
    }, 60000); // Every minute
  }

  private async performHousekeeping(): Promise<void> {
    // Clean up old alerts
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);

    for (const [alertId, alert] of this.recentAlerts.entries()) {
      if (alert.resolved && new Date(alert.triggeredAt) < oneDayAgo) {
        this.recentAlerts.delete(alertId);
      }
    }

    // Update user profiles periodically
    // Implementation would query recent events and update profiles
  }

  private async loadDetectionRules(): Promise<void> {
    // Load default detection rules
    const defaultRules: PatternDetectionRule[] = [
      {
        id: 'failed-logins',
        name: 'Multiple Failed Logins',
        description: 'Multiple login failures from same IP',
        type: AlertType.FAILED_LOGIN_ATTEMPTS,
        severity: AlertSeverity.MEDIUM,
        enabled: true,
        timeWindow: 15,
        threshold: 5,
        conditions: [
          { field: 'action.type', operator: 'equals', value: ActionType.LOGIN },
          {
            field: 'action.result',
            operator: 'equals',
            value: ActionResult.FAILURE,
          },
        ],
        actions: ['block_ip', 'notify_admin'],
      },
    ];

    for (const rule of defaultRules) {
      this.detectionRules.set(rule.id, rule);
    }
  }

  private async loadUserProfiles(): Promise<void> {
    // Load user behavioral profiles from storage
    // Implementation would query historical data to build profiles
  }

  /**
   * Close service and cleanup
   */
  async close(): Promise<void> {
    this.logger.info('Audit analytics service closed');
  }
}
