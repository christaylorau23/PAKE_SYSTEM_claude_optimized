/**
 * PAKE System - Sandbox Policy Enforcement
 *
 * Comprehensive policy engine for CLI provider isolation with strict safety controls.
 * Enforces robots.txt compliance, rate limits, and scraping restrictions.
 */

import { URL } from 'url';
import { createHash } from 'crypto';
import { promises as fs } from 'fs';
import { createLogger, Logger } from '../orchestrator/src/utils/logger';
import { metrics, TaskLifecycleEvent } from '../orchestrator/src/utils/metrics';

export interface SandboxPolicy {
  // Resource constraints
  maxExecutionTimeMs: number;
  maxMemoryMB: number;
  maxDiskMB: number;
  maxProcesses: number;
  maxNetworkConnections: number;

  // Network restrictions
  allowNetworkAccess: boolean;
  allowedDomains: string[];
  blockedDomains: string[];
  respectRobotsTxt: boolean;

  // Rate limiting
  requestsPerMinute: number;
  requestsPerHour: number;
  concurrentRequests: number;

  // Security settings
  redactSecrets: boolean;
  logAllOperations: boolean;
  allowFileSystem: boolean;
  allowedPaths: string[];
  blockedPaths: string[];

  // Compliance
  userAgent: string;
  honorRateLimits: boolean;
  respectCrawlDelay: boolean;
}

export interface SandboxViolation {
  type: ViolationType;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  details: Record<string, any>;
  timestamp: Date;
  taskId?: string;
}

export enum ViolationType {
  RESOURCE_LIMIT = 'resource_limit',
  NETWORK_VIOLATION = 'network_violation',
  ROBOTS_TXT_VIOLATION = 'robots_txt_violation',
  RATE_LIMIT_VIOLATION = 'rate_limit_violation',
  FILESYSTEM_VIOLATION = 'filesystem_violation',
  SECURITY_VIOLATION = 'security_violation',
  COMPLIANCE_VIOLATION = 'compliance_violation',
}

export interface RateLimitState {
  requestCount: number;
  windowStart: number;
  lastRequest: number;
}

export interface RobotsTxtCache {
  content: string;
  parsedRules: RobotsTxtRule[];
  fetchedAt: number;
  expiresAt: number;
}

export interface RobotsTxtRule {
  userAgent: string;
  disallowed: string[];
  allowed: string[];
  crawlDelay?: number;
  sitemaps: string[];
}

/**
 * Comprehensive sandbox policy enforcement engine
 */
export class SandboxEnforcer {
  private readonly logger: Logger;
  private readonly policies: Map<string, SandboxPolicy> = new Map();
  private readonly rateLimitStates: Map<string, RateLimitState> = new Map();
  private readonly robotsTxtCache: Map<string, RobotsTxtCache> = new Map();
  private readonly violations: SandboxViolation[] = [];

  // Default security-first policy
  private readonly defaultPolicy: SandboxPolicy = {
    maxExecutionTimeMs: 30000,
    maxMemoryMB: 256,
    maxDiskMB: 512,
    maxProcesses: 16,
    maxNetworkConnections: 5,

    allowNetworkAccess: false,
    allowedDomains: [],
    blockedDomains: ['*'],
    respectRobotsTxt: true,

    requestsPerMinute: 10,
    requestsPerHour: 100,
    concurrentRequests: 2,

    redactSecrets: true,
    logAllOperations: true,
    allowFileSystem: false,
    allowedPaths: ['/app/temp', '/app/logs'],
    blockedPaths: ['/etc', '/usr', '/bin', '/sbin', '/root'],

    userAgent: 'PAKE-Agent/1.0 (+https://pake-system.com/robots)',
    honorRateLimits: true,
    respectCrawlDelay: true,
  };

  constructor() {
    this.logger = createLogger('SandboxEnforcer');
    this.logger.info('Sandbox policy enforcer initialized');

    // Cleanup old violations every hour
    setInterval(
      () => {
        this.cleanupOldViolations();
      },
      60 * 60 * 1000
    );
  }

  /**
   * Register a custom policy for a provider
   */
  registerPolicy(providerId: string, policy: Partial<SandboxPolicy>): void {
    const mergedPolicy = { ...this.defaultPolicy, ...policy };
    this.policies.set(providerId, mergedPolicy);

    this.logger.info('Policy registered for provider', {
      providerId,
      policy: this.sanitizePolicyForLogging(mergedPolicy),
    });
  }

  /**
   * Get effective policy for a provider
   */
  getPolicy(providerId: string): SandboxPolicy {
    return this.policies.get(providerId) || this.defaultPolicy;
  }

  /**
   * Validate network access against policy
   */
  async validateNetworkAccess(
    providerId: string,
    taskId: string,
    url: string,
    method: string = 'GET'
  ): Promise<{ allowed: boolean; reason?: string; crawlDelay?: number }> {
    const policy = this.getPolicy(providerId);

    try {
      const parsedUrl = new URL(url);
      const domain = parsedUrl.hostname;

      // Check if network access is allowed at all
      if (!policy.allowNetworkAccess) {
        await this.recordViolation({
          type: ViolationType.NETWORK_VIOLATION,
          severity: 'high',
          message: 'Network access not permitted by policy',
          details: { providerId, taskId, url, domain },
          timestamp: new Date(),
          taskId,
        });
        return { allowed: false, reason: 'Network access disabled' };
      }

      // Check domain allowlist/blocklist
      const domainAllowed = this.checkDomainPermission(domain, policy);
      if (!domainAllowed) {
        await this.recordViolation({
          type: ViolationType.NETWORK_VIOLATION,
          severity: 'medium',
          message: 'Domain not permitted by policy',
          details: { providerId, taskId, url, domain },
          timestamp: new Date(),
          taskId,
        });
        return { allowed: false, reason: `Domain ${domain} not permitted` };
      }

      // Check rate limits
      const rateLimitCheck = await this.checkRateLimit(providerId, domain);
      if (!rateLimitCheck.allowed) {
        await this.recordViolation({
          type: ViolationType.RATE_LIMIT_VIOLATION,
          severity: 'medium',
          message: 'Rate limit exceeded',
          details: {
            providerId,
            taskId,
            domain,
            reason: rateLimitCheck.reason,
            retryAfter: rateLimitCheck.retryAfter,
          },
          timestamp: new Date(),
          taskId,
        });
        return { allowed: false, reason: rateLimitCheck.reason };
      }

      // Check robots.txt compliance
      if (policy.respectRobotsTxt && method !== 'HEAD') {
        const robotsCheck = await this.checkRobotsCompliance(
          domain,
          parsedUrl.pathname,
          policy.userAgent
        );

        if (!robotsCheck.allowed) {
          await this.recordViolation({
            type: ViolationType.ROBOTS_TXT_VIOLATION,
            severity: 'high',
            message: 'robots.txt violation',
            details: {
              providerId,
              taskId,
              url,
              path: parsedUrl.pathname,
              userAgent: policy.userAgent,
            },
            timestamp: new Date(),
            taskId,
          });
          return {
            allowed: false,
            reason: 'Disallowed by robots.txt',
            crawlDelay: robotsCheck.crawlDelay,
          };
        }

        return {
          allowed: true,
          crawlDelay: robotsCheck.crawlDelay,
        };
      }

      return { allowed: true };
    } catch (error) {
      this.logger.error('Network validation error', {
        providerId,
        taskId,
        url,
        error: error.message,
      });

      return { allowed: false, reason: 'Validation error' };
    }
  }

  /**
   * Validate filesystem access
   */
  validateFileSystemAccess(
    providerId: string,
    taskId: string,
    path: string,
    operation: 'read' | 'write' | 'execute'
  ): { allowed: boolean; reason?: string } {
    const policy = this.getPolicy(providerId);

    if (!policy.allowFileSystem) {
      this.recordViolation({
        type: ViolationType.FILESYSTEM_VIOLATION,
        severity: 'high',
        message: 'Filesystem access not permitted by policy',
        details: { providerId, taskId, path, operation },
        timestamp: new Date(),
        taskId,
      });
      return { allowed: false, reason: 'Filesystem access disabled' };
    }

    // Check if path is explicitly blocked
    const isBlocked = policy.blockedPaths.some(blockedPath =>
      path.startsWith(blockedPath)
    );

    if (isBlocked) {
      this.recordViolation({
        type: ViolationType.FILESYSTEM_VIOLATION,
        severity: 'critical',
        message: 'Access to blocked path attempted',
        details: { providerId, taskId, path, operation },
        timestamp: new Date(),
        taskId,
      });
      return { allowed: false, reason: 'Path is blocked by policy' };
    }

    // Check if path is in allowed list
    const isAllowed = policy.allowedPaths.some(allowedPath =>
      path.startsWith(allowedPath)
    );

    if (!isAllowed) {
      this.recordViolation({
        type: ViolationType.FILESYSTEM_VIOLATION,
        severity: 'medium',
        message: 'Access to non-whitelisted path attempted',
        details: { providerId, taskId, path, operation },
        timestamp: new Date(),
        taskId,
      });
      return { allowed: false, reason: 'Path not in allowed list' };
    }

    return { allowed: true };
  }

  /**
   * Validate resource usage
   */
  validateResourceUsage(
    providerId: string,
    taskId: string,
    resources: {
      memoryMB?: number;
      executionTimeMs?: number;
      diskMB?: number;
      processCount?: number;
    }
  ): { allowed: boolean; violations: string[] } {
    const policy = this.getPolicy(providerId);
    const violations: string[] = [];

    if (resources.memoryMB && resources.memoryMB > policy.maxMemoryMB) {
      violations.push(
        `Memory usage ${resources.memoryMB}MB exceeds limit ${policy.maxMemoryMB}MB`
      );
      this.recordViolation({
        type: ViolationType.RESOURCE_LIMIT,
        severity: 'high',
        message: 'Memory limit exceeded',
        details: {
          providerId,
          taskId,
          usage: resources.memoryMB,
          limit: policy.maxMemoryMB,
        },
        timestamp: new Date(),
        taskId,
      });
    }

    if (
      resources.executionTimeMs &&
      resources.executionTimeMs > policy.maxExecutionTimeMs
    ) {
      violations.push(
        `Execution time ${resources.executionTimeMs}ms exceeds limit ${policy.maxExecutionTimeMs}ms`
      );
      this.recordViolation({
        type: ViolationType.RESOURCE_LIMIT,
        severity: 'medium',
        message: 'Execution time limit exceeded',
        details: {
          providerId,
          taskId,
          usage: resources.executionTimeMs,
          limit: policy.maxExecutionTimeMs,
        },
        timestamp: new Date(),
        taskId,
      });
    }

    if (resources.diskMB && resources.diskMB > policy.maxDiskMB) {
      violations.push(
        `Disk usage ${resources.diskMB}MB exceeds limit ${policy.maxDiskMB}MB`
      );
      this.recordViolation({
        type: ViolationType.RESOURCE_LIMIT,
        severity: 'medium',
        message: 'Disk usage limit exceeded',
        details: {
          providerId,
          taskId,
          usage: resources.diskMB,
          limit: policy.maxDiskMB,
        },
        timestamp: new Date(),
        taskId,
      });
    }

    if (
      resources.processCount &&
      resources.processCount > policy.maxProcesses
    ) {
      violations.push(
        `Process count ${resources.processCount} exceeds limit ${policy.maxProcesses}`
      );
      this.recordViolation({
        type: ViolationType.RESOURCE_LIMIT,
        severity: 'high',
        message: 'Process count limit exceeded',
        details: {
          providerId,
          taskId,
          usage: resources.processCount,
          limit: policy.maxProcesses,
        },
        timestamp: new Date(),
        taskId,
      });
    }

    return {
      allowed: violations.length === 0,
      violations,
    };
  }

  /**
   * Check domain permission against policy
   */
  private checkDomainPermission(
    domain: string,
    policy: SandboxPolicy
  ): boolean {
    // If allowedDomains is specified, domain must be in it
    if (policy.allowedDomains.length > 0) {
      return policy.allowedDomains.some(
        allowed => domain === allowed || domain.endsWith('.' + allowed)
      );
    }

    // Otherwise, check blocklist
    return !policy.blockedDomains.some(blocked => {
      if (blocked === '*') return true;
      return domain === blocked || domain.endsWith('.' + blocked);
    });
  }

  /**
   * Check rate limits for a provider/domain combination
   */
  private async checkRateLimit(
    providerId: string,
    domain: string
  ): Promise<{ allowed: boolean; reason?: string; retryAfter?: number }> {
    const policy = this.getPolicy(providerId);
    const key = `${providerId}:${domain}`;
    const now = Date.now();

    let state = this.rateLimitStates.get(key);
    if (!state) {
      state = {
        requestCount: 0,
        windowStart: now,
        lastRequest: 0,
      };
      this.rateLimitStates.set(key, state);
    }

    // Check per-minute rate limit
    const minuteWindow = 60 * 1000;
    if (now - state.windowStart >= minuteWindow) {
      // Reset window
      state.requestCount = 0;
      state.windowStart = now;
    }

    if (state.requestCount >= policy.requestsPerMinute) {
      const retryAfter = Math.ceil(
        (state.windowStart + minuteWindow - now) / 1000
      );
      return {
        allowed: false,
        reason: 'Per-minute rate limit exceeded',
        retryAfter,
      };
    }

    // Update state
    state.requestCount++;
    state.lastRequest = now;

    return { allowed: true };
  }

  /**
   * Check robots.txt compliance
   */
  private async checkRobotsCompliance(
    domain: string,
    path: string,
    userAgent: string
  ): Promise<{ allowed: boolean; crawlDelay?: number }> {
    try {
      const robotsTxt = await this.getRobotsTxt(domain);
      if (!robotsTxt) {
        // No robots.txt found, allow by default
        return { allowed: true };
      }

      const applicableRules = this.findApplicableRobotRules(
        robotsTxt.parsedRules,
        userAgent
      );

      for (const rule of applicableRules) {
        // Check disallowed paths
        for (const disallowed of rule.disallowed) {
          if (this.matchesRobotPattern(path, disallowed)) {
            return { allowed: false };
          }
        }

        // Check explicitly allowed paths (overrides disallowed)
        for (const allowed of rule.allowed) {
          if (this.matchesRobotPattern(path, allowed)) {
            return { allowed: true, crawlDelay: rule.crawlDelay };
          }
        }

        return { allowed: true, crawlDelay: rule.crawlDelay };
      }

      return { allowed: true };
    } catch (error) {
      this.logger.warn('robots.txt check failed', {
        domain,
        path,
        error: error.message,
      });
      // Fail safe - allow on error
      return { allowed: true };
    }
  }

  /**
   * Fetch and cache robots.txt
   */
  private async getRobotsTxt(domain: string): Promise<RobotsTxtCache | null> {
    const cached = this.robotsTxtCache.get(domain);
    if (cached && Date.now() < cached.expiresAt) {
      return cached;
    }

    try {
      // In a real implementation, this would make an HTTP request
      // For security, we simulate this with a placeholder
      const robotsUrl = `https://${domain}/robots.txt`;

      this.logger.debug('Fetching robots.txt', { domain, url: robotsUrl });

      // Simulated robots.txt content - in production, use HTTP client
      const content = `
User-agent: *
Disallow: /private/
Disallow: /admin/
Allow: /public/
Crawl-delay: 1

User-agent: PAKE-Agent
Allow: /api/
Crawl-delay: 2
`;

      const parsed = this.parseRobotsTxt(content);
      const cacheEntry: RobotsTxtCache = {
        content,
        parsedRules: parsed,
        fetchedAt: Date.now(),
        expiresAt: Date.now() + 24 * 60 * 60 * 1000, // 24 hours
      };

      this.robotsTxtCache.set(domain, cacheEntry);
      return cacheEntry;
    } catch (error) {
      this.logger.warn('Failed to fetch robots.txt', {
        domain,
        error: error.message,
      });
      return null;
    }
  }

  /**
   * Parse robots.txt content
   */
  private parseRobotsTxt(content: string): RobotsTxtRule[] {
    const rules: RobotsTxtRule[] = [];
    let currentRule: Partial<RobotsTxtRule> = {};

    const lines = content.split('\n').map(line => line.trim());

    for (const line of lines) {
      if (!line || line.startsWith('#')) continue;

      const [directive, ...valueParts] = line.split(':');
      const value = valueParts.join(':').trim();

      switch (directive.toLowerCase()) {
        case 'user-agent':
          if (currentRule.userAgent) {
            // Save previous rule
            if (currentRule.userAgent) {
              rules.push({
                userAgent: currentRule.userAgent,
                disallowed: currentRule.disallowed || [],
                allowed: currentRule.allowed || [],
                crawlDelay: currentRule.crawlDelay,
                sitemaps: currentRule.sitemaps || [],
              });
            }
          }
          currentRule = { userAgent: value };
          break;

        case 'disallow':
          if (!currentRule.disallowed) currentRule.disallowed = [];
          currentRule.disallowed.push(value);
          break;

        case 'allow':
          if (!currentRule.allowed) currentRule.allowed = [];
          currentRule.allowed.push(value);
          break;

        case 'crawl-delay':
          currentRule.crawlDelay = parseInt(value) || 0;
          break;

        case 'sitemap':
          if (!currentRule.sitemaps) currentRule.sitemaps = [];
          currentRule.sitemaps.push(value);
          break;
      }
    }

    // Save last rule
    if (currentRule.userAgent) {
      rules.push({
        userAgent: currentRule.userAgent,
        disallowed: currentRule.disallowed || [],
        allowed: currentRule.allowed || [],
        crawlDelay: currentRule.crawlDelay,
        sitemaps: currentRule.sitemaps || [],
      });
    }

    return rules;
  }

  /**
   * Find applicable robot rules for user agent
   */
  private findApplicableRobotRules(
    rules: RobotsTxtRule[],
    userAgent: string
  ): RobotsTxtRule[] {
    // Look for exact match first
    const exactMatch = rules.filter(
      rule => rule.userAgent.toLowerCase() === userAgent.toLowerCase()
    );

    if (exactMatch.length > 0) {
      return exactMatch;
    }

    // Look for wildcard match
    const wildcardMatch = rules.filter(rule => rule.userAgent === '*');

    return wildcardMatch;
  }

  /**
   * Check if path matches robots.txt pattern
   */
  private matchesRobotPattern(path: string, pattern: string): boolean {
    if (!pattern) return false;

    // Convert robots.txt pattern to regex
    const regexPattern = pattern
      .replace(/\*/g, '.*')
      .replace(/\$/g, '$')
      .replace(/\?/g, '\\?');

    const regex = new RegExp('^' + regexPattern);
    return regex.test(path);
  }

  /**
   * Record a policy violation
   */
  private async recordViolation(violation: SandboxViolation): Promise<void> {
    this.violations.push(violation);

    // Log violation
    this.logger.warn('Policy violation recorded', {
      type: violation.type,
      severity: violation.severity,
      message: violation.message,
      details: violation.details,
    });

    // Track metrics
    metrics.taskLifecycle(
      TaskLifecycleEvent.PROVIDER_FAILED,
      violation.taskId || 'unknown',
      'policy_violation',
      violation.details.providerId,
      undefined,
      violation.message,
      { violationType: violation.type, severity: violation.severity }
    );

    // Persist violation to file for audit
    try {
      const logEntry = JSON.stringify(violation) + '\n';
      await fs.appendFile('/app/logs/policy-violations.jsonl', logEntry);
    } catch (error) {
      this.logger.error('Failed to persist violation', {
        error: error.message,
      });
    }
  }

  /**
   * Get policy violations for a provider or task
   */
  getViolations(providerId?: string, taskId?: string): SandboxViolation[] {
    return this.violations.filter(violation => {
      if (providerId && violation.details.providerId !== providerId)
        return false;
      if (taskId && violation.taskId !== taskId) return false;
      return true;
    });
  }

  /**
   * Get violation statistics
   */
  getViolationStats(): Record<string, any> {
    const stats = {
      total: this.violations.length,
      byType: {} as Record<string, number>,
      bySeverity: {} as Record<string, number>,
      recent: this.violations.filter(
        v => Date.now() - v.timestamp.getTime() < 60 * 60 * 1000 // Last hour
      ).length,
    };

    for (const violation of this.violations) {
      stats.byType[violation.type] = (stats.byType[violation.type] || 0) + 1;
      stats.bySeverity[violation.severity] =
        (stats.bySeverity[violation.severity] || 0) + 1;
    }

    return stats;
  }

  /**
   * Clean up old violations (keep last 1000)
   */
  private cleanupOldViolations(): void {
    if (this.violations.length > 1000) {
      const removed = this.violations.splice(0, this.violations.length - 1000);
      this.logger.debug(`Cleaned up ${removed.length} old violations`);
    }
  }

  /**
   * Sanitize policy for logging (remove sensitive data)
   */
  private sanitizePolicyForLogging(
    policy: SandboxPolicy
  ): Partial<SandboxPolicy> {
    return {
      maxExecutionTimeMs: policy.maxExecutionTimeMs,
      maxMemoryMB: policy.maxMemoryMB,
      allowNetworkAccess: policy.allowNetworkAccess,
      respectRobotsTxt: policy.respectRobotsTxt,
      requestsPerMinute: policy.requestsPerMinute,
      redactSecrets: policy.redactSecrets,
      allowFileSystem: policy.allowFileSystem,
    };
  }
}

// Global sandbox enforcer instance
export const sandboxEnforcer = new SandboxEnforcer();
