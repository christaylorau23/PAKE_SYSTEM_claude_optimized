import express from 'express';
import { knowledgeService } from '../services/knowledgeService.js';
import { logger } from '../utils/logger.js';

const router = express.Router();

// Get all documents with optional filtering
router.get('/documents', async (req, res) => {
  try {
    const { category, tags, limit = 50, offset = 0 } = req.query;

    const parsedLimit = parseInt(limit);
    const parsedOffset = parseInt(offset);
    const parsedTags = tags
      ? Array.isArray(tags)
        ? tags
        : tags.split(',')
      : undefined;

    const result = await knowledgeService.getAllDocuments({
      category,
      tags: parsedTags,
      limit: parsedLimit,
      offset: parsedOffset,
    });

    logger.info(`📚 Retrieved ${result.documents.length} documents`, {
      category,
      tags: parsedTags,
      limit: parsedLimit,
      offset: parsedOffset,
      total: result.total,
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
    logger.error('Failed to retrieve documents:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve documents',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

// Get document by ID
router.get('/documents/:id(*)', async (req, res) => {
  try {
    const { id } = req.params;
    const document = await knowledgeService.getDocumentById(id);

    if (!document) {
      logger.warn(`Document not found: ${id}`);
      return res.status(404).json({
        success: false,
        error: 'Document not found',
        message: `No document found with ID: ${id}`,
        requestId: req.correlationId,
      });
    }

    logger.info(`📄 Retrieved document: ${id}`);

    res.json({
      success: true,
      data: document,
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error(`Failed to retrieve document ${req.params.id}:`, error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve document',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

// Get documents by category
router.get('/categories/:category/documents', async (req, res) => {
  try {
    const { category } = req.params;
    const documents = await knowledgeService.getDocumentsByCategory(category);

    logger.info(
      `📁 Retrieved ${documents.length} documents from category: ${category}`
    );

    res.json({
      success: true,
      data: {
        category,
        documents,
        total: documents.length,
      },
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error(
      `Failed to retrieve documents for category ${req.params.category}:`,
      error
    );
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve documents',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

// Get all categories
router.get('/categories', async (req, res) => {
  try {
    const categories = await knowledgeService.getCategories();

    logger.debug(`📂 Retrieved ${categories.length} categories`);

    res.json({
      success: true,
      data: {
        categories,
        total: categories.length,
      },
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error('Failed to retrieve categories:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve categories',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

// Get all tags
router.get('/tags', async (req, res) => {
  try {
    const tags = await knowledgeService.getTags();

    logger.debug(`🏷️ Retrieved ${tags.length} tags`);

    res.json({
      success: true,
      data: {
        tags,
        total: tags.length,
      },
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error('Failed to retrieve tags:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve tags',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

// Get knowledge statistics
router.get('/stats', async (req, res) => {
  try {
    const stats = await knowledgeService.getKnowledgeStats();

    logger.debug('📊 Retrieved knowledge statistics');

    res.json({
      success: true,
      data: stats,
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error('Failed to retrieve knowledge statistics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve statistics',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

// Refresh knowledge base (force reload)
router.post('/refresh', async (req, res) => {
  try {
    logger.info('🔄 Manual knowledge base refresh requested');

    // This would reload the entire knowledge base
    await knowledgeService.loadKnowledgeBase();

    const stats = await knowledgeService.getKnowledgeStats();

    logger.info('✅ Knowledge base refreshed successfully');

    res.json({
      success: true,
      message: 'Knowledge base refreshed successfully',
      data: stats,
      metadata: {
        timestamp: new Date().toISOString(),
        requestId: req.correlationId,
      },
    });
  } catch (error) {
    logger.error('Failed to refresh knowledge base:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to refresh knowledge base',
      message: error.message,
      requestId: req.correlationId,
    });
  }
});

export { router as knowledgeRoutes };
