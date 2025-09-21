/**
 * PAKE System Service Mesh Entry Point
 * Orchestrates all consolidated services with proper initialization and health monitoring
 */

import { APIGateway, defaultGatewayConfig } from './gateway/api_gateway';
import { ServiceRegistry } from './gateway/service_registry';
import { CircuitBreakerManager } from './gateway/circuit_breaker';
import { AuthService } from './services/consolidated/auth_service';
import { DataService } from './services/consolidated/data_service';
import { AIService } from './services/consolidated/ai_service';
import { SecretsValidator } from './utils/secrets_validator';
import { Logger } from './utils/logger';

export interface ServiceMeshConfig {
  gateway: {
    port: number;
    cors: {
      origin: string[];
      credentials: boolean;
    };
  };
  services: {
    auth: {
      enabled: boolean;
      port: number;
    };
    data: {
      enabled: boolean;
      database: boolean;
      redis: boolean;
    };
    ai: {
      enabled: boolean;
      providers: string[];
    };
  };
  monitoring: {
    healthCheckInterval: number;
    metricsInterval: number;
  };
}

export class ServiceMesh {
  private logger: Logger;
  private config: ServiceMeshConfig;
  private gateway: APIGateway;
  private serviceRegistry: ServiceRegistry;
  private circuitBreakerManager: CircuitBreakerManager;

  // Consolidated services
  private authService: AuthService;
  private dataService: DataService;
  private aiService: AIService;

  // Health monitoring
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private metricsInterval: NodeJS.Timeout | null = null;
  private isRunning: boolean = false;

  constructor(config: ServiceMeshConfig) {
    this.config = config;
    this.logger = new Logger('ServiceMesh');

    // Initialize service registry
    this.serviceRegistry = new ServiceRegistry();

    // Initialize circuit breaker manager
    this.circuitBreakerManager = new CircuitBreakerManager();

    // Initialize consolidated services
    this.authService = new AuthService();
    this.dataService = new DataService();
    this.aiService = new AIService();

    // Initialize API Gateway
    this.gateway = new APIGateway({
      ...defaultGatewayConfig,
      port: config.gateway.port,
      cors: config.gateway.cors,
    });
  }

  /**
   * Initialize and start the service mesh
   */
  public async start(): Promise<void> {
    try {
      this.logger.info('Starting PAKE Service Mesh...');

      // Validate secrets first
      SecretsValidator.validateAllSecrets();

      // Register services
      await this.registerServices();

      // Start API Gateway
      await this.gateway.start();

      // Start health monitoring
      this.startHealthMonitoring();

      // Start metrics collection
      this.startMetricsCollection();

      this.isRunning = true;

      this.logger.info('Service Mesh started successfully', {
        gatewayPort: this.config.gateway.port,
        servicesRegistered: this.serviceRegistry.getServiceCount(),
      });
    } catch (error) {
      this.logger.error('Failed to start Service Mesh', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Register all services with the service registry
   */
  private async registerServices(): Promise<void> {
    try {
      // Register Auth Service
      if (this.config.services.auth.enabled) {
        this.serviceRegistry.registerService({
          name: 'auth-service',
          host: 'localhost',
          port: this.config.services.auth.port,
          protocol: 'http',
          version: '1.0.0',
          healthCheckPath: '/health',
          tags: ['authentication', 'security'],
          metadata: {
            type: 'consolidated',
            consolidatedServices: ['auth', 'authentication', 'security'],
          },
        });

        // Create circuit breaker for auth service
        this.circuitBreakerManager.createCircuitBreaker({
          failureThreshold: 5,
          timeout: 30000,
          serviceName: 'auth-service',
        });
      }

      // Register Data Service
      if (this.config.services.data.enabled) {
        this.serviceRegistry.registerService({
          name: 'data-service',
          host: 'localhost',
          port: 3002,
          protocol: 'http',
          version: '1.0.0',
          healthCheckPath: '/health',
          tags: ['database', 'cache', 'storage'],
          metadata: {
            type: 'consolidated',
            consolidatedServices: ['database', 'caching', 'connectors'],
            features: {
              database: this.config.services.data.database,
              redis: this.config.services.data.redis,
            },
          },
        });

        // Create circuit breaker for data service
        this.circuitBreakerManager.createCircuitBreaker({
          failureThreshold: 3,
          timeout: 30000,
          serviceName: 'data-service',
        });
      }

      // Register AI Service
      if (this.config.services.ai.enabled) {
        this.serviceRegistry.registerService({
          name: 'ai-service',
          host: 'localhost',
          port: 3003,
          protocol: 'http',
          version: '1.0.0',
          healthCheckPath: '/health',
          tags: ['ai', 'agents', 'llm'],
          metadata: {
            type: 'consolidated',
            consolidatedServices: [
              'ai',
              'agent-runtime',
              'agents',
              'autonomous-agents',
              'voice-agents',
            ],
            providers: this.config.services.ai.providers,
          },
        });

        // Create circuit breaker for AI service
        this.circuitBreakerManager.createCircuitBreaker({
          failureThreshold: 3,
          timeout: 60000,
          serviceName: 'ai-service',
        });
      }

      this.logger.info('Services registered successfully', {
        count: this.serviceRegistry.getServiceCount(),
      });
    } catch (error) {
      this.logger.error('Failed to register services', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Start health monitoring
   */
  private startHealthMonitoring(): void {
    this.healthCheckInterval = setInterval(async () => {
      try {
        await this.performHealthChecks();
      } catch (error) {
        this.logger.error('Health check failed', {
          error: error.message,
        });
      }
    }, this.config.monitoring.healthCheckInterval);

    this.logger.info('Health monitoring started', {
      interval: this.config.monitoring.healthCheckInterval,
    });
  }

  /**
   * Start metrics collection
   */
  private startMetricsCollection(): void {
    this.metricsInterval = setInterval(() => {
      try {
        this.collectMetrics();
      } catch (error) {
        this.logger.error('Metrics collection failed', {
          error: error.message,
        });
      }
    }, this.config.monitoring.metricsInterval);

    this.logger.info('Metrics collection started', {
      interval: this.config.monitoring.metricsInterval,
    });
  }

  /**
   * Perform health checks on all services
   */
  private async performHealthChecks(): Promise<void> {
    const healthStatus = {
      timestamp: new Date().toISOString(),
      services: {} as Record<string, any>,
    };

    // Check data service health
    if (this.config.services.data.enabled) {
      healthStatus.services['data-service'] =
        await this.dataService.healthCheck();
    }

    // Check AI service health
    if (this.config.services.ai.enabled) {
      healthStatus.services['ai-service'] = await this.aiService.healthCheck();
    }

    // Check circuit breaker health
    healthStatus.services['circuit-breakers'] =
      this.circuitBreakerManager.getHealthStatus();

    // Log health status
    this.logger.debug('Health check completed', healthStatus);
  }

  /**
   * Collect service metrics
   */
  private collectMetrics(): void {
    const metrics = {
      timestamp: new Date().toISOString(),
      serviceRegistry: this.serviceRegistry.getStatistics(),
      circuitBreakers: this.circuitBreakerManager.getAllMetrics(),
      services: {} as Record<string, any>,
    };

    // Collect data service metrics
    if (this.config.services.data.enabled) {
      metrics.services['data-service'] = this.dataService.getStatistics();
    }

    // Collect AI service metrics
    if (this.config.services.ai.enabled) {
      metrics.services['ai-service'] = this.aiService.getStatistics();
    }

    // Log metrics
    this.logger.debug('Metrics collected', metrics);
  }

  /**
   * Get service mesh status
   */
  public getStatus(): {
    running: boolean;
    services: any;
    health: any;
    metrics: any;
  } {
    return {
      running: this.isRunning,
      services: this.serviceRegistry.getServiceStatuses(),
      health: this.circuitBreakerManager.getHealthStatus(),
      metrics: {
        serviceRegistry: this.serviceRegistry.getStatistics(),
        circuitBreakers: this.circuitBreakerManager.getAllMetrics(),
      },
    };
  }

  /**
   * Gracefully shutdown the service mesh
   */
  public async shutdown(): Promise<void> {
    try {
      this.logger.info('Shutting down Service Mesh...');

      this.isRunning = false;

      // Stop monitoring
      if (this.healthCheckInterval) {
        clearInterval(this.healthCheckInterval);
        this.healthCheckInterval = null;
      }

      if (this.metricsInterval) {
        clearInterval(this.metricsInterval);
        this.metricsInterval = null;
      }

      // Close service connections
      await this.dataService.close();

      // Clear service registry
      this.serviceRegistry.clear();

      this.logger.info('Service Mesh shutdown completed');
    } catch (error) {
      this.logger.error('Error during shutdown', {
        error: error.message,
      });
    }
  }

  /**
   * Get consolidated services
   */
  public getServices(): {
    auth: AuthService;
    data: DataService;
    ai: AIService;
  } {
    return {
      auth: this.authService,
      data: this.dataService,
      ai: this.aiService,
    };
  }

  /**
   * Get service registry
   */
  public getServiceRegistry(): ServiceRegistry {
    return this.serviceRegistry;
  }

  /**
   * Get circuit breaker manager
   */
  public getCircuitBreakerManager(): CircuitBreakerManager {
    return this.circuitBreakerManager;
  }
}

// Default configuration
export const defaultServiceMeshConfig: ServiceMeshConfig = {
  gateway: {
    port: parseInt(process.env.GATEWAY_PORT || '3001'),
    cors: {
      origin: process.env.CORS_ORIGINS?.split(',') || ['http://localhost:3000'],
      credentials: true,
    },
  },
  services: {
    auth: {
      enabled: true,
      port: 3002,
    },
    data: {
      enabled: true,
      database: true,
      redis: true,
    },
    ai: {
      enabled: true,
      providers: ['claude', 'gemini'],
    },
  },
  monitoring: {
    healthCheckInterval: 30000, // 30 seconds
    metricsInterval: 60000, // 1 minute
  },
};

// Main entry point
export async function startServiceMesh(
  config: ServiceMeshConfig = defaultServiceMeshConfig
): Promise<ServiceMesh> {
  const serviceMesh = new ServiceMesh(config);
  await serviceMesh.start();
  return serviceMesh;
}
