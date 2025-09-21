import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import { Neo4jService } from '@/services/neo4j';
import { GraphManager } from '@/services/graph-manager';
import { EntityExtractor } from '@/services/entity-extractor';
import { GraphConstructor } from '@/services/graph-constructor';
import { ReasoningEngine } from '@/services/reasoning-engine';
import { SearchEngine } from '@/services/search-engine';
import { MultiModalPipelineIntegration } from '@/integrations/multimodal-pipeline';
import graphRoutes, { initializeRoutes } from '@/api/graph-routes';
import { neo4jConfig } from '@/config/database';
import { logger, serviceLogger } from '@/utils/logger';
import { createServer } from 'http';

class KnowledgeGraphService {
  private app: express.Application;
  private server?: any;
  private neo4jService?: Neo4jService;
  private graphManager?: GraphManager;
  private entityExtractor?: EntityExtractor;
  private graphConstructor?: GraphConstructor;
  private reasoningEngine?: ReasoningEngine;
  private searchEngine?: SearchEngine;
  private pipelineIntegration?: MultiModalPipelineIntegration;
  private isInitialized = false;

  constructor() {
    this.app = express();
    this.setupMiddleware();
    this.setupErrorHandling();
  }

  private setupMiddleware(): void {
    // Security middleware
    this.app.use(
      helmet({
        contentSecurityPolicy: {
          directives: {
            defaultSrc: ["'self'"],
            styleSrc: ["'self'", "'unsafe-inline'"],
            scriptSrc: ["'self'"],
            imgSrc: ["'self'", 'data:', 'https:'],
            connectSrc: ["'self'"],
            fontSrc: ["'self'"],
            objectSrc: ["'none'"],
            mediaSrc: ["'self'"],
            frameSrc: ["'none'"],
          },
        },
        crossOriginEmbedderPolicy: false,
      })
    );

    // CORS configuration
    this.app.use(
      cors({
        origin:
          process.env.NODE_ENV === 'production'
            ? [
                'https://dashboard.pake.local',
                'https://pake-dashboard.herokuapp.com',
              ]
            : [
                'http://localhost:3000',
                'http://localhost:3001',
                'http://localhost:3002',
              ],
        credentials: true,
        methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
      })
    );

    // General middleware
    this.app.use(compression());
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    // Request logging
    this.app.use((req, res, next) => {
      const start = Date.now();
      res.on('finish', () => {
        const duration = Date.now() - start;
        serviceLogger.info(`${req.method} ${req.path}`, {
          status: res.statusCode,
          duration,
          ip: req.ip,
          userAgent: req.get('User-Agent'),
        });
      });
      next();
    });
  }

  private setupErrorHandling(): void {
    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({
        success: false,
        error: 'Endpoint not found',
        path: req.originalUrl,
        method: req.method,
      });
    });

    // Global error handler
    this.app.use(
      (
        error: Error,
        req: express.Request,
        res: express.Response,
        next: express.NextFunction
      ) => {
        serviceLogger.error('Unhandled error:', error);

        if (res.headersSent) {
          return next(error);
        }

        res.status(500).json({
          success: false,
          error:
            process.env.NODE_ENV === 'production'
              ? 'Internal server error'
              : error.message,
          ...(process.env.NODE_ENV === 'development' && { stack: error.stack }),
        });
      }
    );

    // Unhandled promise rejection
    process.on('unhandledRejection', (reason, promise) => {
      serviceLogger.error('Unhandled Promise Rejection:', { reason, promise });
    });

    // Uncaught exception
    process.on('uncaughtException', error => {
      serviceLogger.error('Uncaught Exception:', error);
      process.exit(1);
    });
  }

  async initialize(): Promise<void> {
    if (this.isInitialized) {
      serviceLogger.warn('Service already initialized');
      return;
    }

    try {
      serviceLogger.info('Initializing Knowledge Graph Service...');

      // Initialize Neo4j connection
      serviceLogger.info('Connecting to Neo4j...');
      this.neo4jService = new Neo4jService(neo4jConfig);
      await this.neo4jService.connect();
      serviceLogger.info('Neo4j connection established');

      // Initialize Graph Manager
      serviceLogger.info('Initializing Graph Manager...');
      this.graphManager = new GraphManager(this.neo4jService);
      await this.graphManager.initialize();
      serviceLogger.info('Graph Manager initialized');

      // Initialize Entity Extractor
      serviceLogger.info('Initializing Entity Extractor...');
      this.entityExtractor = new EntityExtractor({
        confidenceThreshold: parseFloat(
          process.env.ENTITY_CONFIDENCE_THRESHOLD || '0.7'
        ),
        enableNERProcessing: process.env.ENABLE_NER_PROCESSING !== 'false',
        maxEntitiesPerDocument: parseInt(
          process.env.MAX_ENTITIES_PER_DOCUMENT || '100'
        ),
        minEntityLength: parseInt(process.env.MIN_ENTITY_LENGTH || '2'),
        enableConceptExtraction:
          process.env.ENABLE_CONCEPT_EXTRACTION !== 'false',
      });
      serviceLogger.info('Entity Extractor initialized');

      // Initialize Graph Constructor
      serviceLogger.info('Initializing Graph Constructor...');
      this.graphConstructor = new GraphConstructor(
        this.graphManager,
        this.entityExtractor,
        {
          batchSize: parseInt(process.env.GRAPH_BATCH_SIZE || '10'),
          enableRealTimeProcessing:
            process.env.ENABLE_REALTIME_PROCESSING !== 'false',
          maxConcurrentProcessing: parseInt(
            process.env.MAX_CONCURRENT_PROCESSING || '5'
          ),
          similarityThreshold: parseFloat(
            process.env.SIMILARITY_THRESHOLD || '0.8'
          ),
          enableIncrementalUpdates:
            process.env.ENABLE_INCREMENTAL_UPDATES !== 'false',
        }
      );
      await this.graphConstructor.initialize();
      serviceLogger.info('Graph Constructor initialized');

      // Initialize Reasoning Engine
      serviceLogger.info('Initializing Reasoning Engine...');
      this.reasoningEngine = new ReasoningEngine(
        this.graphManager,
        this.neo4jService,
        {
          maxPathLength: parseInt(process.env.MAX_PATH_LENGTH || '5'),
          similarityThreshold: parseFloat(
            process.env.REASONING_SIMILARITY_THRESHOLD || '0.7'
          ),
          enableCaching: process.env.ENABLE_REASONING_CACHE !== 'false',
          cacheTimeout: parseInt(
            process.env.REASONING_CACHE_TIMEOUT || '300000'
          ),
          maxInsightsPerRun: parseInt(process.env.MAX_INSIGHTS_PER_RUN || '10'),
        }
      );
      await this.reasoningEngine.initialize();
      serviceLogger.info('Reasoning Engine initialized');

      // Initialize Search Engine
      serviceLogger.info('Initializing Search Engine...');
      this.searchEngine = new SearchEngine(
        this.neo4jService,
        this.graphManager,
        this.reasoningEngine,
        {
          maxResults: parseInt(process.env.SEARCH_MAX_RESULTS || '50'),
          enableFuzzySearch: process.env.ENABLE_FUZZY_SEARCH !== 'false',
          enableSemanticSearch: process.env.ENABLE_SEMANTIC_SEARCH !== 'false',
          caching: {
            enabled: process.env.ENABLE_SEARCH_CACHE !== 'false',
            ttl: parseInt(process.env.SEARCH_CACHE_TTL || '300000'),
            maxCacheSize: parseInt(process.env.SEARCH_CACHE_SIZE || '1000'),
          },
        }
      );
      await this.searchEngine.initialize();
      serviceLogger.info('Search Engine initialized');

      // Initialize Pipeline Integration
      if (process.env.ENABLE_MULTIMODAL_INTEGRATION !== 'false') {
        serviceLogger.info('Initializing MultiModal Pipeline Integration...');
        this.pipelineIntegration = new MultiModalPipelineIntegration(
          this.graphConstructor,
          this.entityExtractor,
          this.graphManager,
          {
            multimodalApiUrl:
              process.env.MULTIMODAL_API_URL || 'http://localhost:3003/api',
            pollInterval: parseInt(
              process.env.PIPELINE_POLL_INTERVAL || '5000'
            ),
            batchSize: parseInt(process.env.PIPELINE_BATCH_SIZE || '10'),
            enableRealTimeSync: process.env.ENABLE_REALTIME_SYNC !== 'false',
          }
        );
        await this.pipelineIntegration.start();
        serviceLogger.info('MultiModal Pipeline Integration started');
      }

      // Initialize API routes
      initializeRoutes(this.graphManager, this.reasoningEngine);
      this.app.use('/api/graph', graphRoutes);

      // Health check endpoint
      this.app.get('/health', (req, res) => {
        res.json({
          success: true,
          service: 'knowledge-graph',
          status: 'healthy',
          timestamp: new Date().toISOString(),
          version: process.env.npm_package_version || '1.0.0',
          components: {
            neo4j: this.neo4jService?.isConnected() || false,
            graphManager: !!this.graphManager,
            entityExtractor: !!this.entityExtractor,
            graphConstructor: !!this.graphConstructor,
            reasoningEngine: !!this.reasoningEngine,
            searchEngine: !!this.searchEngine,
            pipelineIntegration: this.pipelineIntegration
              ? 'active'
              : 'disabled',
          },
        });
      });

      // Service info endpoint
      this.app.get('/api/info', async (req, res) => {
        try {
          const stats = this.graphManager
            ? await this.graphManager.getGraphStatistics()
            : null;
          const pipelineStats = this.pipelineIntegration
            ? await this.pipelineIntegration.getProcessingStats()
            : null;

          res.json({
            success: true,
            service: {
              name: 'PAKE Knowledge Graph Service',
              version: process.env.npm_package_version || '1.0.0',
              environment: process.env.NODE_ENV || 'development',
              uptime: process.uptime(),
              memory: process.memoryUsage(),
            },
            graph: stats,
            pipeline: pipelineStats,
          });
        } catch (error) {
          res.status(500).json({
            success: false,
            error: 'Failed to get service info',
          });
        }
      });

      this.isInitialized = true;
      serviceLogger.info('Knowledge Graph Service initialization complete');
    } catch (error) {
      serviceLogger.error('Failed to initialize service:', error);
      await this.cleanup();
      throw error;
    }
  }

  async start(
    port: number = parseInt(process.env.PORT || '3005')
  ): Promise<void> {
    if (!this.isInitialized) {
      throw new Error('Service must be initialized before starting');
    }

    return new Promise((resolve, reject) => {
      try {
        this.server = createServer(this.app);

        this.server.listen(port, '0.0.0.0', () => {
          serviceLogger.info(`Knowledge Graph Service started on port ${port}`);
          serviceLogger.info(`Health check: http://localhost:${port}/health`);
          serviceLogger.info(
            `API endpoint: http://localhost:${port}/api/graph`
          );
          resolve();
        });

        this.server.on('error', (error: Error) => {
          serviceLogger.error('Server error:', error);
          reject(error);
        });

        // Graceful shutdown
        const shutdown = async (signal: string) => {
          serviceLogger.info(`Received ${signal}, shutting down gracefully...`);

          if (this.server) {
            this.server.close(async () => {
              await this.cleanup();
              process.exit(0);
            });
          } else {
            await this.cleanup();
            process.exit(0);
          }
        };

        process.on('SIGTERM', () => shutdown('SIGTERM'));
        process.on('SIGINT', () => shutdown('SIGINT'));
      } catch (error) {
        serviceLogger.error('Failed to start server:', error);
        reject(error);
      }
    });
  }

  private async cleanup(): Promise<void> {
    serviceLogger.info('Cleaning up resources...');

    try {
      // Stop pipeline integration
      if (this.pipelineIntegration) {
        await this.pipelineIntegration.stop();
        serviceLogger.info('Pipeline integration stopped');
      }

      // Stop graph constructor
      if (this.graphConstructor) {
        await this.graphConstructor.stop();
        serviceLogger.info('Graph constructor stopped');
      }

      // Stop reasoning engine
      if (this.reasoningEngine) {
        await this.reasoningEngine.stop();
        serviceLogger.info('Reasoning engine stopped');
      }

      // Stop search engine
      if (this.searchEngine) {
        await this.searchEngine.stop();
        serviceLogger.info('Search engine stopped');
      }

      // Close Neo4j connection
      if (this.neo4jService) {
        await this.neo4jService.close();
        serviceLogger.info('Neo4j connection closed');
      }

      serviceLogger.info('Cleanup complete');
    } catch (error) {
      serviceLogger.error('Error during cleanup:', error);
    }
  }

  // Public getters for testing/monitoring
  get isHealthy(): boolean {
    return (
      this.isInitialized &&
      (this.neo4jService?.isConnected() || false) &&
      !!this.graphManager
    );
  }

  get components() {
    return {
      neo4jService: this.neo4jService,
      graphManager: this.graphManager,
      entityExtractor: this.entityExtractor,
      graphConstructor: this.graphConstructor,
      reasoningEngine: this.reasoningEngine,
      searchEngine: this.searchEngine,
      pipelineIntegration: this.pipelineIntegration,
    };
  }
}

// Main execution
async function main() {
  const service = new KnowledgeGraphService();

  try {
    await service.initialize();
    await service.start();
  } catch (error) {
    logger.error('Failed to start Knowledge Graph Service:', error);
    process.exit(1);
  }
}

// Run if this file is executed directly
if (require.main === module) {
  main();
}

export { KnowledgeGraphService };
export default KnowledgeGraphService;
