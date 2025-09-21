import express from 'express';
import { knowledgeService } from '../services/knowledgeService.js';
import { searchService } from '../services/searchService.js';
import { logger } from '../utils/logger.js';

const router = express.Router();

// Basic health check
router.get('/', async (req, res) => {
  try {
    const stats = await knowledgeService.getKnowledgeStats();
    const searchStats = await searchService.getSearchStats();

    const health = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      service: 'pake-knowledge-api',
      version: process.env.npm_package_version || '1.0.0',
      environment: process.env.NODE_ENV || 'development',
      uptime: process.uptime(),
      memory: {
        used: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
        total: Math.round(process.memoryUsage().heapTotal / 1024 / 1024),
        rss: Math.round(process.memoryUsage().rss / 1024 / 1024),
      },
      knowledge: {
        totalDocuments: stats.totalDocuments,
        totalCategories: stats.totalCategories,
        totalTags: stats.totalTags,
        totalWords: stats.totalWords,
        lastUpdated: stats.lastUpdated,
      },
      search: {
        status: searchStats.searchIndexStatus,
        threshold: searchStats.fuseOptions.threshold,
      },
    };

    res.json(health);
  } catch (error) {
    logger.error('Health check failed:', error);
    res.status(503).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: error.message,
    });
  }
});

// Detailed health check
router.get('/detailed', async (req, res) => {
  try {
    const stats = await knowledgeService.getKnowledgeStats();
    const searchStats = await searchService.getSearchStats();
    const categories = await knowledgeService.getCategories();
    const tags = await knowledgeService.getTags();

    const detailedHealth = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      service: 'pake-knowledge-api',
      version: process.env.npm_package_version || '1.0.0',
      environment: process.env.NODE_ENV || 'development',
      uptime: process.uptime(),

      system: {
        nodeVersion: process.version,
        platform: process.platform,
        arch: process.arch,
        memory: {
          used: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
          total: Math.round(process.memoryUsage().heapTotal / 1024 / 1024),
          rss: Math.round(process.memoryUsage().rss / 1024 / 1024),
          external: Math.round(process.memoryUsage().external / 1024 / 1024),
        },
        cpu: {
          userTime: process.cpuUsage().user,
          systemTime: process.cpuUsage().system,
        },
      },

      knowledge: {
        ...stats,
        categories: categories.slice(0, 10), // Top 10 categories
        popularTags: tags.slice(0, 10), // Top 10 tags
        paths: {
          knowledgeVaultPath: process.env.KNOWLEDGE_VAULT_PATH,
          pakeSystemPath: process.env.PAKE_SYSTEM_PATH,
        },
      },

      search: searchStats,

      configuration: {
        maxSearchResults: process.env.MAX_SEARCH_RESULTS,
        searchFuzzyThreshold: process.env.SEARCH_FUZZY_THRESHOLD,
        watchDebounceMs: process.env.WATCH_DEBOUNCE_MS,
        rateLimitWindowMs: process.env.RATE_LIMIT_WINDOW_MS,
        rateLimitMaxRequests: process.env.RATE_LIMIT_MAX_REQUESTS,
      },
    };

    res.json(detailedHealth);
  } catch (error) {
    logger.error('Detailed health check failed:', error);
    res.status(503).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: error.message,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined,
    });
  }
});

// Readiness probe
router.get('/ready', async (req, res) => {
  try {
    const stats = await knowledgeService.getKnowledgeStats();

    if (stats.totalDocuments > 0) {
      res.json({
        status: 'ready',
        timestamp: new Date().toISOString(),
        documentsLoaded: stats.totalDocuments,
      });
    } else {
      res.status(503).json({
        status: 'not-ready',
        timestamp: new Date().toISOString(),
        reason: 'No documents loaded yet',
      });
    }
  } catch (error) {
    logger.error('Readiness check failed:', error);
    res.status(503).json({
      status: 'not-ready',
      timestamp: new Date().toISOString(),
      error: error.message,
    });
  }
});

// Liveness probe
router.get('/live', (req, res) => {
  res.json({
    status: 'alive',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
});

export { router as healthRoutes };
