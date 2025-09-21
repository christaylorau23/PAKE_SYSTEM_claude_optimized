/**
 * Service Registry for Service Discovery
 * Manages service registration, health checks, and load balancing
 */

import { Logger } from '../utils/logger';

export interface ServiceInfo {
  name: string;
  host: string;
  port: number;
  protocol: 'http' | 'https';
  version: string;
  healthCheckPath: string;
  metadata: Record<string, unknown>;
  tags: string[];
  lastHealthCheck: number;
  isHealthy: boolean;
  loadBalancer: LoadBalancer;
}

export interface LoadBalancer {
  algorithm: 'round-robin' | 'least-connections' | 'weighted';
  weights?: Record<string, number>;
  maxConnections?: number;
  currentConnections: number;
}

export interface HealthCheck {
  path: string;
  interval: number;
  timeout: number;
  retries: number;
  expectedStatus: number;
}

export interface ServiceRegistration {
  name: string;
  host: string;
  port: number;
  protocol: 'http' | 'https';
  version: string;
  healthCheckPath: string;
  metadata?: Record<string, unknown>;
  tags?: string[];
  loadBalancer?: Partial<LoadBalancer>;
}

export class ServiceRegistry {
  private services: Map<string, ServiceInfo> = new Map();
  private healthCheckIntervals: Map<string, NodeJS.Timeout> = new Map();
  private logger: Logger;

  constructor() {
    this.logger = new Logger('ServiceRegistry');
  }

  /**
   * Register a new service
   */
  public registerService(registration: ServiceRegistration): void {
    const serviceInfo: ServiceInfo = {
      name: registration.name,
      host: registration.host,
      port: registration.port,
      protocol: registration.protocol,
      version: registration.version,
      healthCheckPath: registration.healthCheckPath,
      metadata: registration.metadata || {},
      tags: registration.tags || [],
      lastHealthCheck: 0,
      isHealthy: false,
      loadBalancer: {
        algorithm: 'round-robin',
        currentConnections: 0,
        ...registration.loadBalancer,
      },
    };

    this.services.set(registration.name, serviceInfo);
    this.startHealthCheck(registration.name);

    this.logger.info('Service registered', {
      name: registration.name,
      host: registration.host,
      port: registration.port,
      version: registration.version,
    });
  }

  /**
   * Unregister a service
   */
  public unregisterService(serviceName: string): void {
    const service = this.services.get(serviceName);
    if (!service) {
      this.logger.warn('Attempted to unregister unknown service', {
        service: serviceName,
      });
      return;
    }

    // Stop health check
    const interval = this.healthCheckIntervals.get(serviceName);
    if (interval) {
      clearInterval(interval);
      this.healthCheckIntervals.delete(serviceName);
    }

    this.services.delete(serviceName);

    this.logger.info('Service unregistered', {
      name: serviceName,
    });
  }

  /**
   * Get service by name
   */
  public getService(serviceName: string): ServiceInfo | undefined {
    const service = this.services.get(serviceName);
    if (!service || !service.isHealthy) {
      return undefined;
    }
    return service;
  }

  /**
   * Get all services
   */
  public getAllServices(): ServiceInfo[] {
    return Array.from(this.services.values());
  }

  /**
   * Get healthy services only
   */
  public getHealthyServices(): ServiceInfo[] {
    return Array.from(this.services.values()).filter(
      service => service.isHealthy
    );
  }

  /**
   * Get services by tag
   */
  public getServicesByTag(tag: string): ServiceInfo[] {
    return Array.from(this.services.values()).filter(
      service => service.tags.includes(tag) && service.isHealthy
    );
  }

  /**
   * Get service statuses
   */
  public getServiceStatuses(): Record<string, unknown> {
    const statuses: Record<string, unknown> = {};

    for (const [name, service] of this.services) {
      statuses[name] = {
        healthy: service.isHealthy,
        lastHealthCheck: service.lastHealthCheck,
        version: service.version,
        tags: service.tags,
        connections: service.loadBalancer.currentConnections,
      };
    }

    return statuses;
  }

  /**
   * Start health check for a service
   */
  private startHealthCheck(serviceName: string): void {
    const service = this.services.get(serviceName);
    if (!service) return;

    const healthCheck = {
      path: service.healthCheckPath,
      interval: 30000, // 30 seconds
      timeout: 5000, // 5 seconds
      retries: 3,
      expectedStatus: 200,
    };

    const performHealthCheck = async () => {
      try {
        const url = `${service.protocol}://${service.host}:${service.port}${healthCheck.path}`;

        const controller = new AbortController();
        const timeoutId = setTimeout(
          () => controller.abort(),
          healthCheck.timeout
        );

        const response = await fetch(url, {
          method: 'GET',
          signal: controller.signal,
          headers: {
            'User-Agent': 'PAKE-ServiceRegistry/1.0',
          },
        });

        clearTimeout(timeoutId);

        if (response.status === healthCheck.expectedStatus) {
          this.updateServiceHealth(serviceName, true);
        } else {
          this.updateServiceHealth(serviceName, false);
        }
      } catch (error) {
        this.logger.warn('Health check failed', {
          service: serviceName,
          error: error.message,
        });
        this.updateServiceHealth(serviceName, false);
      }
    };

    // Perform initial health check
    performHealthCheck();

    // Set up interval
    const interval = setInterval(performHealthCheck, healthCheck.interval);
    this.healthCheckIntervals.set(serviceName, interval);
  }

  /**
   * Update service health status
   */
  private updateServiceHealth(serviceName: string, isHealthy: boolean): void {
    const service = this.services.get(serviceName);
    if (!service) return;

    const wasHealthy = service.isHealthy;
    service.isHealthy = isHealthy;
    service.lastHealthCheck = Date.now();

    if (wasHealthy !== isHealthy) {
      this.logger.info('Service health status changed', {
        service: serviceName,
        healthy: isHealthy,
        host: service.host,
        port: service.port,
      });
    }
  }

  /**
   * Increment connection count for load balancing
   */
  public incrementConnections(serviceName: string): void {
    const service = this.services.get(serviceName);
    if (service) {
      service.loadBalancer.currentConnections++;
    }
  }

  /**
   * Decrement connection count for load balancing
   */
  public decrementConnections(serviceName: string): void {
    const service = this.services.get(serviceName);
    if (service && service.loadBalancer.currentConnections > 0) {
      service.loadBalancer.currentConnections--;
    }
  }

  /**
   * Get service URL
   */
  public getServiceUrl(serviceName: string): string | undefined {
    const service = this.getService(serviceName);
    if (!service) return undefined;

    return `${service.protocol}://${service.host}:${service.port}`;
  }

  /**
   * Get service endpoint URL
   */
  public getServiceEndpoint(
    serviceName: string,
    path: string
  ): string | undefined {
    const baseUrl = this.getServiceUrl(serviceName);
    if (!baseUrl) return undefined;

    return `${baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
  }

  /**
   * Check if service exists
   */
  public hasService(serviceName: string): boolean {
    return this.services.has(serviceName);
  }

  /**
   * Get service count
   */
  public getServiceCount(): number {
    return this.services.size;
  }

  /**
   * Get healthy service count
   */
  public getHealthyServiceCount(): number {
    return this.getHealthyServices().length;
  }

  /**
   * Clear all services
   */
  public clear(): void {
    // Stop all health checks
    for (const interval of this.healthCheckIntervals.values()) {
      clearInterval(interval);
    }
    this.healthCheckIntervals.clear();

    // Clear services
    this.services.clear();

    this.logger.info('All services cleared');
  }

  /**
   * Get registry statistics
   */
  public getStatistics(): {
    totalServices: number;
    healthyServices: number;
    unhealthyServices: number;
    totalConnections: number;
  } {
    const healthyServices = this.getHealthyServices();
    const totalConnections = healthyServices.reduce(
      (sum, service) => sum + service.loadBalancer.currentConnections,
      0
    );

    return {
      totalServices: this.services.size,
      healthyServices: healthyServices.length,
      unhealthyServices: this.services.size - healthyServices.length,
      totalConnections,
    };
  }
}

/**
 * Service Discovery Client
 */
export class ServiceDiscoveryClient {
  private registry: ServiceRegistry;
  private logger: Logger;

  constructor(registry: ServiceRegistry) {
    this.registry = registry;
    this.logger = new Logger('ServiceDiscoveryClient');
  }

  /**
   * Discover service endpoint
   */
  public discoverService(
    serviceName: string,
    path: string = ''
  ): string | undefined {
    const endpoint = this.registry.getServiceEndpoint(serviceName, path);

    if (!endpoint) {
      this.logger.warn('Service not found or unhealthy', {
        service: serviceName,
        path,
      });
    }

    return endpoint;
  }

  /**
   * Get service with load balancing
   */
  public getServiceWithLoadBalancing(
    serviceName: string
  ): ServiceInfo | undefined {
    const service = this.registry.getService(serviceName);
    if (!service) return undefined;

    // Simple round-robin implementation
    // In a real implementation, this would be more sophisticated
    this.registry.incrementConnections(serviceName);

    return service;
  }

  /**
   * Release service connection
   */
  public releaseServiceConnection(serviceName: string): void {
    this.registry.decrementConnections(serviceName);
  }
}
