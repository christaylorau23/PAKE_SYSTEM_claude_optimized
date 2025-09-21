#!/usr/bin/env node

/**
 * PAKE System Service Mesh Startup Script
 * Launches the consolidated service mesh with proper error handling and graceful shutdown
 */

import { startServiceMesh, defaultServiceMeshConfig } from './service_mesh';
import { Logger } from './utils/logger';

const logger = new Logger('ServiceMeshStartup');

async function main() {
  try {
    logger.info('🚀 Starting PAKE System Service Mesh...');

    // Start the service mesh
    const serviceMesh = await startServiceMesh(defaultServiceMeshConfig);

    logger.info('✅ Service Mesh started successfully!', {
      status: serviceMesh.getStatus(),
    });

    // Handle graceful shutdown
    process.on('SIGINT', async () => {
      logger.info('🛑 Received SIGINT, shutting down gracefully...');
      await serviceMesh.shutdown();
      process.exit(0);
    });

    process.on('SIGTERM', async () => {
      logger.info('🛑 Received SIGTERM, shutting down gracefully...');
      await serviceMesh.shutdown();
      process.exit(0);
    });

    process.on('uncaughtException', async error => {
      logger.error('💥 Uncaught exception', {
        error: error.message,
        stack: error.stack,
      });
      await serviceMesh.shutdown();
      process.exit(1);
    });

    process.on('unhandledRejection', async (reason, promise) => {
      logger.error('💥 Unhandled rejection', { reason, promise });
      await serviceMesh.shutdown();
      process.exit(1);
    });

    // Keep the process running
    setInterval(() => {
      const status = serviceMesh.getStatus();
      logger.debug('Service Mesh Status', {
        running: status.running,
        healthyServices: Object.values(status.services).filter(
          (s: unknown) => (s as { healthy: boolean }).healthy
        ).length,
        totalServices: Object.keys(status.services).length,
      });
    }, 60000); // Log status every minute
  } catch (error) {
    logger.error('❌ Failed to start Service Mesh', {
      error: error.message,
      stack: error.stack,
    });
    process.exit(1);
  }
}

// Start the service mesh
main().catch(error => {
  logger.error('💥 Fatal error in main', {
    error: error.message,
    stack: error.stack,
  });
  process.exit(1);
});
