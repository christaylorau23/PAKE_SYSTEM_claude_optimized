import express from 'express';
import { searchService } from '../services/searchService.js';
import { logger } from '../utils/logger.js';

const router = express.Router();

// Main search endpoint
router.get('/', async (req, res) => {
  try {
    const {
      q: query,
      limit = 20,
      category,
      tags,
      includeContent = false,
    } = req.query;

    if (!query || query.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Query parameter is required',
        message: 'Please provide a search query using the "q" parameter',
        requestId: req.correlationId,
      });
    }

    const parsedLimit = Math.min(parseInt(limit) || 20, 100); // Max 100 results
    const parsedTags = tags
      ? Array.isArray(tags)
        ? tags
        : tags.split(',')
      : undefined;
    const parsedIncludeContent =
      includeContent === 'true' || includeContent === '1';

    const result = await searchService.search(query, {
      limit: parsedLimit,
      category,
      tags: parsedTags,
      includeContent: parsedIncludeContent,
    });

    res.json({
      success: true,
      data: result,
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error(`Search failed for query "${req.query.q}":`, error);
    res.status(500).json({
      success: false,
      error: 'Search operation failed',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

// Search by category
router.get('/category/:category', async (req, res) => {
  try {
    const { category } = req.params;
    const { q: query = '', limit = 20, includeContent = false } = req.query;

    const parsedLimit = Math.min(parseInt(limit) || 20, 100);
    const parsedIncludeContent =
      includeContent === 'true' || includeContent === '1';

    const result = await searchService.searchByCategory(category, query, {
      limit: parsedLimit,
      includeContent: parsedIncludeContent,
    });

    res.json({
      success: true,
      data: result,
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error(`Category search failed for "${req.params.category}":`, error);
    res.status(500).json({
      success: false,
      error: 'Category search failed',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

// Search by tags
router.get('/tags/:tags', async (req, res) => {
  try {
    const { tags } = req.params;
    const { q: query = '', limit = 20, includeContent = false } = req.query;

    const parsedTags = tags.split(',');
    const parsedLimit = Math.min(parseInt(limit) || 20, 100);
    const parsedIncludeContent =
      includeContent === 'true' || includeContent === '1';

    const result = await searchService.searchByTags(parsedTags, query, {
      limit: parsedLimit,
      includeContent: parsedIncludeContent,
    });

    res.json({
      success: true,
      data: result,
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error(`Tag search failed for tags "${req.params.tags}":`, error);
    res.status(500).json({
      success: false,
      error: 'Tag search failed',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

// Get search suggestions/autocomplete
router.get('/suggestions', async (req, res) => {
  try {
    const { q: partialQuery, limit = 10 } = req.query;

    if (!partialQuery || partialQuery.trim().length < 2) {
      return res.json({
        success: true,
        data: {
          suggestions: [],
          query: partialQuery || '',
          message: 'Query too short for suggestions (minimum 2 characters)',
        },
        metadata: {
          timestamp: new Date().toISOString(),
          requestId: req.correlationId,
        },
      });
    }

    const parsedLimit = Math.min(parseInt(limit) || 10, 20); // Max 20 suggestions
    const suggestions = await searchService.getSuggestions(
      partialQuery,
      parsedLimit
    );

    res.json({
      success: true,
      data: {
        suggestions,
        query: partialQuery,
        total: suggestions.length,
      },
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error(`Failed to get suggestions for "${req.query.q}":`, error);
    res.status(500).json({
      success: false,
      error: 'Failed to get suggestions',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

// Get search statistics and configuration
router.get('/stats', async (req, res) => {
  try {
    const stats = await searchService.getSearchStats();

    res.json({
      success: true,
      data: stats,
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error('Failed to retrieve search statistics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve search statistics',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

// Refresh search index
router.post('/refresh', async (req, res) => {
  try {
    logger.info('🔍 Manual search index refresh requested');

    const result = await searchService.refreshIndex();

    logger.info('✅ Search index refreshed successfully');

    res.json({
      success: true,
      data: result,
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error('Failed to refresh search index:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to refresh search index',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

// Advanced search with complex filters
router.post('/advanced', async (req, res) => {
  try {
    const { query, filters = {}, options = {} } = req.body;

    if (!query || query.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Query is required',
        message: 'Please provide a search query in the request body',
        requestId: req.correlationId,
      });
    }

    const searchOptions = {
      limit: Math.min(parseInt(options.limit) || 20, 100),
      includeContent: options.includeContent || false,
      category: filters.category,
      tags: filters.tags,
    };

    const result = await searchService.search(query, searchOptions);

    res.json({
      success: true,
      data: result,
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error(`Advanced search failed:`, error);
    res.status(500).json({
      success: false,
      error: 'Advanced search failed',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

export { router as searchRoutes };
