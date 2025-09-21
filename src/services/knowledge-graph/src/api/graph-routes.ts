import { Router, Request, Response } from 'express';
import { GraphManager } from '@/services/graph-manager';
import { ReasoningEngine } from '@/services/reasoning-engine';
import { logger } from '@/utils/logger';
import { z } from 'zod';

const router = Router();

// Validation schemas
const graphQuerySchema = z.object({
  query: z.string(),
  limit: z.number().min(1).max(1000).optional().default(100),
  nodeTypes: z.array(z.string()).optional(),
  relationshipTypes: z.array(z.string()).optional(),
  filters: z.record(z.any()).optional(),
});

const pathFindingSchema = z.object({
  startNodeId: z.string(),
  endNodeId: z.string(),
  maxDepth: z.number().min(1).max(10).optional().default(5),
  relationshipTypes: z.array(z.string()).optional(),
});

const similaritySearchSchema = z.object({
  nodeId: z.string(),
  threshold: z.number().min(0).max(1).optional().default(0.7),
  limit: z.number().min(1).max(100).optional().default(20),
});

// Graph Manager and Reasoning Engine instances
let graphManager: GraphManager;
let reasoningEngine: ReasoningEngine;

export const initializeRoutes = (gm: GraphManager, re: ReasoningEngine) => {
  graphManager = gm;
  reasoningEngine = re;
};

// GET /api/graph/overview - Get graph statistics and overview
router.get('/overview', async (req: Request, res: Response) => {
  try {
    const stats = await graphManager.getGraphStatistics();
    const recentActivity = await graphManager.getRecentActivity(10);

    res.json({
      success: true,
      data: {
        statistics: stats,
        recentActivity,
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    logger.error('Failed to get graph overview:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve graph overview',
    });
  }
});

// POST /api/graph/query - Execute Cypher queries with validation
router.post('/query', async (req: Request, res: Response) => {
  try {
    const { query, limit, nodeTypes, relationshipTypes, filters } =
      graphQuerySchema.parse(req.body);

    // Execute query with security validation
    const results = await graphManager.executeQuery(query, {
      limit,
      nodeTypes,
      relationshipTypes,
      filters,
    });

    res.json({
      success: true,
      data: results,
      query,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    logger.error('Query execution failed:', error);
    res.status(400).json({
      success: false,
      error: error instanceof Error ? error.message : 'Query execution failed',
    });
  }
});

// GET /api/graph/nodes/:id - Get detailed node information
router.get('/nodes/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const includeRelationships = req.query.relationships === 'true';

    const node = await graphManager.getNode(id);
    if (!node) {
      return res.status(404).json({
        success: false,
        error: 'Node not found',
      });
    }

    let relationships = [];
    if (includeRelationships) {
      relationships = await graphManager.getNodeRelationships(id);
    }

    res.json({
      success: true,
      data: {
        node,
        relationships,
        metadata: {
          includeRelationships,
          relationshipCount: relationships.length,
        },
      },
    });
  } catch (error) {
    logger.error('Failed to get node:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve node information',
    });
  }
});

// POST /api/graph/paths - Find paths between nodes
router.post('/paths', async (req: Request, res: Response) => {
  try {
    const { startNodeId, endNodeId, maxDepth, relationshipTypes } =
      pathFindingSchema.parse(req.body);

    const paths = await reasoningEngine.findPaths(startNodeId, endNodeId, {
      maxDepth,
      relationshipTypes,
    });

    res.json({
      success: true,
      data: {
        paths,
        count: paths.length,
        parameters: { startNodeId, endNodeId, maxDepth, relationshipTypes },
      },
    });
  } catch (error) {
    logger.error('Path finding failed:', error);
    res.status(400).json({
      success: false,
      error: error instanceof Error ? error.message : 'Path finding failed',
    });
  }
});

// POST /api/graph/similarity - Find similar nodes
router.post('/similarity', async (req: Request, res: Response) => {
  try {
    const { nodeId, threshold, limit } = similaritySearchSchema.parse(req.body);

    const similarNodes = await reasoningEngine.findSimilarNodes(
      nodeId,
      threshold,
      limit
    );

    res.json({
      success: true,
      data: {
        similarNodes,
        count: similarNodes.length,
        parameters: { nodeId, threshold, limit },
      },
    });
  } catch (error) {
    logger.error('Similarity search failed:', error);
    res.status(400).json({
      success: false,
      error:
        error instanceof Error ? error.message : 'Similarity search failed',
    });
  }
});

// GET /api/graph/insights - Get automated insights
router.get('/insights', async (req: Request, res: Response) => {
  try {
    const limit = Math.min(parseInt(req.query.limit as string) || 10, 50);
    const types = req.query.types
      ? (req.query.types as string).split(',')
      : undefined;

    const insights = await reasoningEngine.generateInsights({ limit, types });

    res.json({
      success: true,
      data: {
        insights,
        count: insights.length,
        generatedAt: new Date().toISOString(),
      },
    });
  } catch (error) {
    logger.error('Failed to generate insights:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to generate insights',
    });
  }
});

// GET /api/graph/clusters - Get graph clusters
router.get('/clusters', async (req: Request, res: Response) => {
  try {
    const algorithm = (req.query.algorithm as string) || 'louvain';
    const minSize = parseInt(req.query.minSize as string) || 3;

    const clusters = await reasoningEngine.detectCommunities(algorithm, {
      minSize,
    });

    res.json({
      success: true,
      data: {
        clusters,
        count: clusters.length,
        algorithm,
        parameters: { minSize },
      },
    });
  } catch (error) {
    logger.error('Cluster detection failed:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to detect clusters',
    });
  }
});

// GET /api/graph/recommendations/:nodeId - Get recommendations for a node
router.get('/recommendations/:nodeId', async (req: Request, res: Response) => {
  try {
    const { nodeId } = req.params;
    const limit = Math.min(parseInt(req.query.limit as string) || 10, 50);

    const recommendations = await reasoningEngine.getRecommendations(nodeId, {
      limit,
    });

    res.json({
      success: true,
      data: {
        recommendations,
        count: recommendations.length,
        nodeId,
        limit,
      },
    });
  } catch (error) {
    logger.error('Failed to get recommendations:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to generate recommendations',
    });
  }
});

// GET /api/graph/search - Text-based graph search
router.get('/search', async (req: Request, res: Response) => {
  try {
    const query = req.query.q as string;
    const nodeTypes = req.query.types
      ? (req.query.types as string).split(',')
      : undefined;
    const limit = Math.min(parseInt(req.query.limit as string) || 20, 100);

    if (!query || query.trim().length < 2) {
      return res.status(400).json({
        success: false,
        error: 'Search query must be at least 2 characters long',
      });
    }

    const results = await graphManager.searchNodes(query.trim(), {
      nodeTypes,
      limit,
    });

    res.json({
      success: true,
      data: {
        results,
        count: results.length,
        query: query.trim(),
        filters: { nodeTypes, limit },
      },
    });
  } catch (error) {
    logger.error('Graph search failed:', error);
    res.status(500).json({
      success: false,
      error: 'Graph search failed',
    });
  }
});

// WebSocket endpoint for real-time graph updates
router.get('/stream', (req: Request, res: Response) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'Access-Control-Allow-Origin': '*',
  });

  const clientId = Math.random().toString(36).substring(2, 15);
  logger.info(`SSE client connected: ${clientId}`);

  // Send initial connection message
  res.write(
    `data: ${JSON.stringify({ type: 'connection', clientId, timestamp: new Date().toISOString() })}\n\n`
  );

  // Set up graph update listener
  const updateHandler = (update: any) => {
    res.write(
      `data: ${JSON.stringify({ type: 'graph_update', data: update, timestamp: new Date().toISOString() })}\n\n`
    );
  };

  graphManager.on('graph_updated', updateHandler);
  reasoningEngine.on('insight_generated', insight => {
    res.write(
      `data: ${JSON.stringify({ type: 'insight', data: insight, timestamp: new Date().toISOString() })}\n\n`
    );
  });

  // Handle client disconnect
  req.on('close', () => {
    logger.info(`SSE client disconnected: ${clientId}`);
    graphManager.off('graph_updated', updateHandler);
  });

  // Keep connection alive
  const heartbeat = setInterval(() => {
    res.write(
      `data: ${JSON.stringify({ type: 'heartbeat', timestamp: new Date().toISOString() })}\n\n`
    );
  }, 30000);

  req.on('close', () => {
    clearInterval(heartbeat);
  });
});

export default router;
