/**
 * Compliance Reporting Service
 * Generates automated compliance reports for SOC2, HIPAA, GDPR, PCI-DSS
 */

import { v4 as uuidv4 } from 'uuid';
import {
  ComplianceReport,
  ComplianceReportType,
  ComplianceReportSummary,
  AuditEvent,
  AuditQuery,
  ActionType,
  ActionResult,
  ActorType,
} from '../types/audit.types';
import { AuditStorageService } from './AuditStorageService';
import { CryptographicAuditService } from './CryptographicAuditService';
import { Logger } from '../utils/logger';

interface ComplianceMetrics {
  totalEvents: number;
  successfulActions: number;
  failedActions: number;
  uniqueUsers: Set<string>;
  criticalEvents: number;
  securityIncidents: number;
  dataAccess: {
    reads: number;
    writes: number;
    exports: number;
  };
  authentication: {
    logins: number;
    logouts: number;
    failedAttempts: number;
  };
}

interface ComplianceFilter {
  includeActions?: ActionType[];
  excludeActions?: ActionType[];
  includeActors?: ActorType[];
  excludeActors?: ActorType[];
  includeResources?: string[];
  excludeResources?: string[];
  criticalOnly?: boolean;
}

export class ComplianceReportingService {
  private readonly logger = new Logger('ComplianceReportingService');
  private readonly storageService: AuditStorageService;
  private readonly cryptoService: CryptographicAuditService;

  constructor(
    storageService: AuditStorageService,
    cryptoService: CryptographicAuditService
  ) {
    this.storageService = storageService;
    this.cryptoService = cryptoService;
  }

  /**
   * Generate compliance report
   */
  async generateReport(
    type: ComplianceReportType,
    startDate: Date,
    endDate: Date,
    generatedBy: string
  ): Promise<ComplianceReport> {
    try {
      const reportId = uuidv4();

      this.logger.info('Generating compliance report', {
        reportId,
        type,
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
      });

      // Get compliance-specific filter
      const filter = this.getComplianceFilter(type);

      // Query relevant events
      const events = await this.queryComplianceEvents(
        startDate,
        endDate,
        filter
      );

      // Calculate metrics
      const summary = await this.calculateComplianceSummary(events, type);

      // Create report
      const report: ComplianceReport = {
        id: reportId,
        type,
        period: {
          start: startDate.toISOString(),
          end: endDate.toISOString(),
        },
        summary,
        events: events,
        generatedAt: new Date().toISOString(),
        generatedBy,
        signature: '',
      };

      // Sign the report
      report.signature = await this.signReport(report);

      this.logger.info('Compliance report generated successfully', {
        reportId,
        type,
        eventCount: events.length,
        duration: `${Date.now() - Date.parse(report.generatedAt)}ms`,
      });

      return report;
    } catch (error) {
      this.logger.error('Failed to generate compliance report', {
        type,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Generate SOC2 specific report
   */
  async generateSOC2Report(
    startDate: Date,
    endDate: Date,
    generatedBy: string
  ): Promise<ComplianceReport> {
    return this.generateReport(
      ComplianceReportType.SOC2,
      startDate,
      endDate,
      generatedBy
    );
  }

  /**
   * Generate HIPAA specific report
   */
  async generateHIPAAReport(
    startDate: Date,
    endDate: Date,
    generatedBy: string
  ): Promise<ComplianceReport> {
    return this.generateReport(
      ComplianceReportType.HIPAA,
      startDate,
      endDate,
      generatedBy
    );
  }

  /**
   * Generate GDPR specific report
   */
  async generateGDPRReport(
    startDate: Date,
    endDate: Date,
    generatedBy: string
  ): Promise<ComplianceReport> {
    return this.generateReport(
      ComplianceReportType.GDPR,
      startDate,
      endDate,
      generatedBy
    );
  }

  /**
   * Generate PCI-DSS specific report
   */
  async generatePCIDSSReport(
    startDate: Date,
    endDate: Date,
    generatedBy: string
  ): Promise<ComplianceReport> {
    return this.generateReport(
      ComplianceReportType.PCI_DSS,
      startDate,
      endDate,
      generatedBy
    );
  }

  /**
   * Verify report integrity
   */
  async verifyReport(report: ComplianceReport): Promise<boolean> {
    try {
      const expectedSignature = await this.signReport({
        ...report,
        signature: '', // Remove signature for verification
      });

      return expectedSignature === report.signature;
    } catch (error) {
      this.logger.error('Failed to verify report integrity', {
        reportId: report.id,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Get compliance violations
   */
  async getComplianceViolations(
    type: ComplianceReportType,
    startDate: Date,
    endDate: Date
  ): Promise<AuditEvent[]> {
    const violationPatterns = this.getViolationPatterns(type);
    const violations: AuditEvent[] = [];

    for (const pattern of violationPatterns) {
      const query: AuditQuery = {
        startTime: startDate,
        endTime: endDate,
        ...pattern,
      };

      const events = await this.storageService.queryEvents(query);
      violations.push(...events);
    }

    // Remove duplicates
    const uniqueViolations = violations.filter(
      (event, index, self) => index === self.findIndex(e => e.id === event.id)
    );

    return uniqueViolations;
  }

  /**
   * Generate executive summary
   */
  async generateExecutiveSummary(
    type: ComplianceReportType,
    startDate: Date,
    endDate: Date
  ): Promise<{
    overview: string;
    keyFindings: string[];
    recommendations: string[];
    riskAssessment: 'low' | 'medium' | 'high' | 'critical';
  }> {
    const report = await this.generateReport(
      type,
      startDate,
      endDate,
      'system'
    );
    const violations = await this.getComplianceViolations(
      type,
      startDate,
      endDate
    );

    const riskLevel = this.assessRiskLevel(report.summary, violations.length);

    return {
      overview: this.generateOverviewText(report, type),
      keyFindings: this.generateKeyFindings(report, violations),
      recommendations: this.generateRecommendations(type, violations),
      riskAssessment: riskLevel,
    };
  }

  /**
   * Query compliance-specific events
   */
  private async queryComplianceEvents(
    startDate: Date,
    endDate: Date,
    filter: ComplianceFilter
  ): Promise<AuditEvent[]> {
    const query: AuditQuery = {
      startTime: startDate,
      endTime: endDate,
      limit: 50000, // Large limit for compliance reports
    };

    // Apply filters based on compliance type
    const events = await this.storageService.queryEvents(query);

    return events.filter(event => this.matchesComplianceFilter(event, filter));
  }

  /**
   * Calculate compliance summary metrics
   */
  private async calculateComplianceSummary(
    events: AuditEvent[],
    type: ComplianceReportType
  ): Promise<ComplianceReportSummary> {
    const metrics: ComplianceMetrics = {
      totalEvents: events.length,
      successfulActions: 0,
      failedActions: 0,
      uniqueUsers: new Set<string>(),
      criticalEvents: 0,
      securityIncidents: 0,
      dataAccess: { reads: 0, writes: 0, exports: 0 },
      authentication: { logins: 0, logouts: 0, failedAttempts: 0 },
    };

    // Process each event
    for (const event of events) {
      // Track unique users
      if (event.actor.type === ActorType.USER) {
        metrics.uniqueUsers.add(event.actor.id);
      }

      // Count success/failure
      if (event.action.result === ActionResult.SUCCESS) {
        metrics.successfulActions++;
      } else if (
        event.action.result === ActionResult.FAILURE ||
        event.action.result === ActionResult.ERROR ||
        event.action.result === ActionResult.DENIED
      ) {
        metrics.failedActions++;
      }

      // Track data access
      if (event.action.type === ActionType.read) {
        metrics.dataAccess.reads++;
      } else if (
        event.action.type === ActionType.CREATE ||
        event.action.type === ActionType.UPDATE ||
        event.action.type === ActionType.DELETE
      ) {
        metrics.dataAccess.writes++;
      } else if (event.action.type === ActionType.EXPORT) {
        metrics.dataAccess.exports++;
      }

      // Track authentication
      if (event.action.type === ActionType.LOGIN) {
        if (event.action.result === ActionResult.SUCCESS) {
          metrics.authentication.logins++;
        } else {
          metrics.authentication.failedAttempts++;
        }
      } else if (event.action.type === ActionType.LOGOUT) {
        metrics.authentication.logouts++;
      }

      // Identify critical events and security incidents
      if (this.isCriticalEvent(event, type)) {
        metrics.criticalEvents++;
      }

      if (this.isSecurityIncident(event, type)) {
        metrics.securityIncidents++;
      }
    }

    return {
      totalEvents: metrics.totalEvents,
      successfulActions: metrics.successfulActions,
      failedActions: metrics.failedActions,
      uniqueUsers: metrics.uniqueUsers.size,
      criticalEvents: metrics.criticalEvents,
      securityIncidents: metrics.securityIncidents,
      dataAccess: metrics.dataAccess,
      authentication: metrics.authentication,
    };
  }

  /**
   * Get compliance-specific filter
   */
  private getComplianceFilter(type: ComplianceReportType): ComplianceFilter {
    switch (type) {
      case ComplianceReportType.SOC2:
        return {
          includeActions: [
            ActionType.LOGIN,
            ActionType.LOGOUT,
            ActionType.ACCESS_GRANTED,
            ActionType.ACCESS_DENIED,
            ActionType.CREATE,
            ActionType.UPDATE,
            ActionType.DELETE,
            ActionType.EXPORT,
            ActionType.CONFIGURE,
          ],
          includeResources: [
            'user',
            'session',
            'data',
            'system',
            'configuration',
          ],
        };

      case ComplianceReportType.HIPAA:
        return {
          includeActions: [
            ActionType.read,
            ActionType.CREATE,
            ActionType.UPDATE,
            ActionType.DELETE,
            ActionType.EXPORT,
            ActionType.ACCESS_GRANTED,
            ActionType.ACCESS_DENIED,
          ],
          includeResources: ['patient', 'medical', 'health', 'phi'],
        };

      case ComplianceReportType.GDPR:
        return {
          includeActions: [
            ActionType.read,
            ActionType.CREATE,
            ActionType.UPDATE,
            ActionType.DELETE,
            ActionType.EXPORT,
            ActionType.ACCESS_GRANTED,
            ActionType.ACCESS_DENIED,
          ],
          includeResources: ['user', 'personal', 'data', 'profile'],
        };

      case ComplianceReportType.PCI_DSS:
        return {
          includeActions: [
            ActionType.read,
            ActionType.CREATE,
            ActionType.UPDATE,
            ActionType.DELETE,
            ActionType.ACCESS_GRANTED,
            ActionType.ACCESS_DENIED,
          ],
          includeResources: ['payment', 'card', 'financial', 'transaction'],
        };

      default:
        return {}; // No filter for custom reports
    }
  }

  /**
   * Check if event matches compliance filter
   */
  private matchesComplianceFilter(
    event: AuditEvent,
    filter: ComplianceFilter
  ): boolean {
    // Include actions filter
    if (
      filter.includeActions &&
      !filter.includeActions.includes(event.action.type)
    ) {
      return false;
    }

    // Exclude actions filter
    if (
      filter.excludeActions &&
      filter.excludeActions.includes(event.action.type)
    ) {
      return false;
    }

    // Include actors filter
    if (
      filter.includeActors &&
      !filter.includeActors.includes(event.actor.type)
    ) {
      return false;
    }

    // Exclude actors filter
    if (
      filter.excludeActors &&
      filter.excludeActors.includes(event.actor.type)
    ) {
      return false;
    }

    // Include resources filter
    if (
      filter.includeResources &&
      !filter.includeResources.some(resource =>
        event.action.resource.toLowerCase().includes(resource.toLowerCase())
      )
    ) {
      return false;
    }

    // Exclude resources filter
    if (
      filter.excludeResources &&
      filter.excludeResources.some(resource =>
        event.action.resource.toLowerCase().includes(resource.toLowerCase())
      )
    ) {
      return false;
    }

    // Critical only filter
    if (
      filter.criticalOnly &&
      !this.isCriticalEvent(event, ComplianceReportType.CUSTOM)
    ) {
      return false;
    }

    return true;
  }

  /**
   * Check if event is critical
   */
  private isCriticalEvent(
    event: AuditEvent,
    type: ComplianceReportType
  ): boolean {
    // Failed access attempts
    if (
      event.action.result === ActionResult.DENIED ||
      event.action.result === ActionResult.FAILURE
    ) {
      return true;
    }

    // Administrative actions
    if (
      event.action.type === ActionType.CONFIGURE ||
      event.action.type === ActionType.DELETE ||
      event.action.resource.toLowerCase().includes('admin')
    ) {
      return true;
    }

    // Sensitive data access
    if (
      type === ComplianceReportType.HIPAA &&
      (event.action.resource.toLowerCase().includes('patient') ||
        event.action.resource.toLowerCase().includes('medical'))
    ) {
      return true;
    }

    if (
      type === ComplianceReportType.PCI_DSS &&
      (event.action.resource.toLowerCase().includes('payment') ||
        event.action.resource.toLowerCase().includes('card'))
    ) {
      return true;
    }

    return false;
  }

  /**
   * Check if event is security incident
   */
  private isSecurityIncident(
    event: AuditEvent,
    type: ComplianceReportType
  ): boolean {
    // Multiple failed login attempts (would need context from multiple events)
    if (
      event.action.type === ActionType.LOGIN &&
      event.action.result === ActionResult.FAILURE
    ) {
      return true;
    }

    // Unauthorized access attempts
    if (event.action.result === ActionResult.DENIED) {
      return true;
    }

    // Privilege escalation attempts
    if (
      event.action.resource.toLowerCase().includes('role') ||
      event.action.resource.toLowerCase().includes('permission')
    ) {
      return true;
    }

    return false;
  }

  /**
   * Get violation patterns for compliance type
   */
  private getViolationPatterns(
    type: ComplianceReportType
  ): Partial<AuditQuery>[] {
    switch (type) {
      case ComplianceReportType.SOC2:
        return [
          { result: ActionResult.DENIED },
          { result: ActionResult.FAILURE },
          { actionType: ActionType.ACCESS_DENIED },
        ];

      case ComplianceReportType.HIPAA:
        return [
          { result: ActionResult.DENIED },
          { actionType: ActionType.EXPORT },
          { resource: 'patient' },
        ];

      case ComplianceReportType.GDPR:
        return [
          { result: ActionResult.DENIED },
          { actionType: ActionType.EXPORT },
          { resource: 'personal' },
        ];

      case ComplianceReportType.PCI_DSS:
        return [
          { result: ActionResult.DENIED },
          { resource: 'payment' },
          { resource: 'card' },
        ];

      default:
        return [{ result: ActionResult.DENIED }];
    }
  }

  /**
   * Sign compliance report
   */
  private async signReport(
    report: Omit<ComplianceReport, 'signature'>
  ): Promise<string> {
    const reportData = {
      id: report.id,
      type: report.type,
      period: report.period,
      summary: report.summary,
      generatedAt: report.generatedAt,
      generatedBy: report.generatedBy,
    };

    // Use cryptographic service to sign
    const signedEvent = await this.cryptoService.signAuditEvent({
      id: report.id,
      timestamp: report.generatedAt,
      actor: {
        id: 'compliance-service',
        type: ActorType.SYSTEM,
      },
      action: {
        type: ActionType.CREATE,
        resource: 'compliance-report',
        resourceId: report.id,
        result: ActionResult.SUCCESS,
      },
      context: {
        environment: 'production',
        application: 'audit-service',
        version: '1.0.0',
      },
      version: '1.0.0',
    });

    return signedEvent.signature!;
  }

  /**
   * Assess risk level
   */
  private assessRiskLevel(
    summary: ComplianceReportSummary,
    violationCount: number
  ): 'low' | 'medium' | 'high' | 'critical' {
    const errorRate =
      summary.totalEvents > 0
        ? (summary.failedActions / summary.totalEvents) * 100
        : 0;

    if (
      violationCount > 100 ||
      errorRate > 10 ||
      summary.securityIncidents > 50
    ) {
      return 'critical';
    } else if (
      violationCount > 50 ||
      errorRate > 5 ||
      summary.securityIncidents > 20
    ) {
      return 'high';
    } else if (
      violationCount > 10 ||
      errorRate > 2 ||
      summary.securityIncidents > 5
    ) {
      return 'medium';
    } else {
      return 'low';
    }
  }

  /**
   * Generate overview text
   */
  private generateOverviewText(
    report: ComplianceReport,
    type: ComplianceReportType
  ): string {
    const period = `${report.period.start.split('T')[0]} to ${report.period.end.split('T')[0]}`;
    const complianceType = type.toUpperCase().replace('_', '-');

    return (
      `${complianceType} compliance report for the period ${period}. ` +
      `This report covers ${report.summary.totalEvents} audit events from ` +
      `${report.summary.uniqueUsers} unique users with ${report.summary.securityIncidents} ` +
      `security incidents identified.`
    );
  }

  /**
   * Generate key findings
   */
  private generateKeyFindings(
    report: ComplianceReport,
    violations: AuditEvent[]
  ): string[] {
    const findings: string[] = [];

    if (report.summary.securityIncidents > 0) {
      findings.push(
        `${report.summary.securityIncidents} security incidents detected`
      );
    }

    if (violations.length > 0) {
      findings.push(
        `${violations.length} potential compliance violations identified`
      );
    }

    const errorRate =
      (report.summary.failedActions / report.summary.totalEvents) * 100;
    if (errorRate > 5) {
      findings.push(`High error rate detected: ${errorRate.toFixed(2)}%`);
    }

    if (report.summary.authentication.failedAttempts > 100) {
      findings.push(
        `${report.summary.authentication.failedAttempts} failed authentication attempts`
      );
    }

    return findings;
  }

  /**
   * Generate recommendations
   */
  private generateRecommendations(
    type: ComplianceReportType,
    violations: AuditEvent[]
  ): string[] {
    const recommendations: string[] = [];

    if (violations.length > 0) {
      recommendations.push(
        'Review and investigate all identified compliance violations'
      );
    }

    recommendations.push(
      'Implement additional monitoring for critical resource access'
    );
    recommendations.push('Enhance user training on security best practices');

    if (type === ComplianceReportType.SOC2) {
      recommendations.push('Review access control policies and procedures');
    }

    return recommendations;
  }
}
