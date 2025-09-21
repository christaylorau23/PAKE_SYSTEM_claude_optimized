#!/usr/bin/env node
/**
 * PAKE+ Enhanced Obsidian Bridge API v3.0
 *
 * Advanced bidirectional integration with real-time sync, metadata extraction,
 * knowledge graph integration, and ML-powered auto-tagging capabilities.
 */

import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import { promises as fs } from 'fs';
import path from 'path';
import matter from 'gray-matter';
import { v4 as uuidv4 } from 'uuid';
import axios from 'axios';
import chokidar from 'chokidar';
import { EventEmitter } from 'events';

// Enhanced type definitions
interface EnhancedNoteData {
  id?: string;
  title: string;
  content: string;
  type?: 'note' | 'project' | 'resource' | 'daily' | 'system';
  status?: 'draft' | 'verified' | 'archived';
  tags?: string[];
  confidence_score?: number;
  source?: string;
  created_at?: string;
  updated_at?: string;
  ai_summary?: string;
  human_notes?: string;
  verification_status?: 'pending' | 'verified' | 'rejected';
  connections?: string[];
  customFields?: Record<string, any>;
}

interface EnhancedFrontmatterData {
  pake_id: string;
  title: string;
  created: string;
  modified: string;
  type: string;
  status: string;
  confidence_score: number;
  verification_status: string;
  source_uri: string;
  tags: string[];
  connections: string[];
  ai_summary: string;
  human_notes: string;
  customFields?: Record<string, any>;
}

interface ApiResponse<T = any> {
  success: boolean;
  data: T | null;
  error: string | null;
  timestamp: string;
  request_id?: string | undefined;
}

interface SyncEvent {
  type: 'create' | 'update' | 'delete' | 'move';
  filepath: string;
  timestamp: string;
  metadata?: unknown;
}

interface KnowledgeGraphNode {
  id: string;
  title: string;
  type: string;
  connections: string[];
  metadata: Record<string, any>;
}

// Configuration
const CONFIG = {
  PORT: parseInt(process.env.BRIDGE_PORT || '3001'),
  VAULT_PATH:
    process.env.VAULT_PATH ||
    '/root/projects/PAKE_SYSTEM_claude_optimized/vault',
  MCP_SERVER_URL: process.env.MCP_SERVER_URL || 'http://localhost:8000',
  MAX_FILE_SIZE: '50mb',
  LOG_LEVEL: process.env.LOG_LEVEL || 'info',
  SYNC_INTERVAL: parseInt(process.env.SYNC_INTERVAL || '5000'),
  AUTO_TAG_ENABLED: process.env.AUTO_TAG_ENABLED === 'true',
  KNOWLEDGE_GRAPH_ENABLED: process.env.KNOWLEDGE_GRAPH_ENABLED === 'true',
};

const app = express();
const syncEmitter = new EventEmitter();

// Enhanced middleware
app.use(
  cors({
    origin: process.env.ALLOWED_ORIGINS?.split(',') || '*',
    credentials: true,
  })
);

app.use(express.json({ limit: CONFIG.MAX_FILE_SIZE }));
app.use(express.urlencoded({ extended: true }));

// Enhanced logging with request tracing
app.use((req: Request, res: Response, next: NextFunction) => {
  const timestamp = new Date().toISOString();
  const requestId = uuidv4();

  req.headers['x-request-id'] = requestId;
  res.setHeader('x-request-id', requestId);

  console.log(`[${timestamp}] ${req.method} ${req.path} [${requestId}]`);
  next();
});

// Utility functions
const getCurrentTimestamp = (): string => {
  return new Date().toISOString().replace('T', ' ').replace(/\..+/, '');
};

const createEnhancedFrontmatter = (
  data: Partial<EnhancedNoteData>
): EnhancedFrontmatterData => {
  const timestamp = getCurrentTimestamp();
  return {
    pake_id: data.id || uuidv4(),
    title: data.title || 'Untitled Note',
    created: data.created_at || timestamp,
    modified: data.updated_at || timestamp,
    type: data.type || 'note',
    status: data.status || 'draft',
    confidence_score: data.confidence_score || 0.5,
    verification_status: data.verification_status || 'pending',
    source_uri: data.source || 'api://enhanced-bridge',
    tags: data.tags || [],
    connections: data.connections || [],
    ai_summary: data.ai_summary || '',
    human_notes: data.human_notes || '',
    customFields: data.customFields || {},
  };
};

const createApiResponse = <T>(
  success: boolean,
  data: T | null = null,
  error: string | null = null,
  requestId?: string
): ApiResponse<T> => {
  const response: ApiResponse<T> = {
    success,
    data,
    error,
    timestamp: new Date().toISOString(),
  };

  if (requestId) {
    response.request_id = requestId;
  }

  return response;
};

const sanitizeFilename = (title: string): string => {
  return title
    .replace(/[<>:"/\\|?*]/g, '-')
    .replace(/\s+/g, '-')
    .toLowerCase()
    .slice(0, 100);
};

const getFolderPath = (type: string, status: string): string => {
  const folderMap = {
    daily: '01-Daily',
    project: '03-Projects',
    resource: '05-Resources',
    system: '02-Permanent',
  };

  if (status === 'draft') return '00-Inbox';
  if (status === 'verified') return '02-Permanent';
  if (status === 'archived') return '06-Archives';

  return folderMap[type as keyof typeof folderMap] || '00-Inbox';
};

// Enhanced error handling
const errorHandler = (
  error: Error,
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  const requestId = req.headers['x-request-id'] as string;
  console.error(
    `[${new Date().toISOString()}] Error in ${req.method} ${req.path} [${requestId}]:`,
    error
  );

  if (res.headersSent) {
    next(error);
    return;
  }

  const statusCode = error.name === 'ValidationError' ? 400 : 500;
  res
    .status(statusCode)
    .json(createApiResponse(false, null, error.message, requestId));
};

// File watcher for real-time sync
let fileWatcher: chokidar.FSWatcher | null = null;

const initializeFileWatcher = (): void => {
  if (fileWatcher) {
    fileWatcher.close();
  }

  fileWatcher = chokidar.watch(CONFIG.VAULT_PATH, {
    ignored: /(^|[\/\\])\../, // ignore dotfiles
    persistent: true,
    ignoreInitial: true,
    awaitWriteFinish: {
      stabilityThreshold: 1000,
      pollInterval: 100,
    },
  });

  fileWatcher
    .on('add', async filepath => {
      if (filepath.endsWith('.md')) {
        await handleFileChange('create', filepath);
      }
    })
    .on('change', async filepath => {
      if (filepath.endsWith('.md')) {
        await handleFileChange('update', filepath);
      }
    })
    .on('unlink', async filepath => {
      if (filepath.endsWith('.md')) {
        await handleFileChange('delete', filepath);
      }
    })
    .on('error', error => {
      console.error('File watcher error:', error);
    });

  console.log(`📁 File watcher initialized for: ${CONFIG.VAULT_PATH}`);
};

const handleFileChange = async (
  eventType: 'create' | 'update' | 'delete',
  filepath: string
): Promise<void> => {
  try {
    const syncEvent: SyncEvent = {
      type: eventType,
      filepath,
      timestamp: new Date().toISOString(),
    };

    if (eventType !== 'delete') {
      const content = await fs.readFile(filepath, 'utf8');
      const parsed = matter(content);
      syncEvent.metadata = parsed.data;
    }

    // Emit sync event
    syncEmitter.emit('fileChange', syncEvent);

    // Notify MCP server
    try {
      await axios.post(`${CONFIG.MCP_SERVER_URL}/obsidian/sync`, {
        event: syncEvent,
        vault_path: CONFIG.VAULT_PATH,
      });
    } catch (error) {
      console.warn('Failed to notify MCP server of file change:', error);
    }

    console.log(
      `📝 File ${eventType}: ${path.relative(CONFIG.VAULT_PATH, filepath)}`
    );
  } catch (error) {
    console.error(`Error handling file change for ${filepath}:`, error);
  }
};

// Auto-tagging based on ML insights
const generateAutoTags = async (
  content: string,
  title: string
): Promise<string[]> => {
  if (!CONFIG.AUTO_TAG_ENABLED) return [];

  try {
    const response = await axios.post(`${CONFIG.MCP_SERVER_URL}/ml/auto-tag`, {
      content: title + '\n\n' + content,
      max_tags: 5,
    });

    return response.data.tags || [];
  } catch (error) {
    console.warn('Auto-tagging failed:', error);
    return [];
  }
};

// Knowledge graph integration
const updateKnowledgeGraph = async (
  noteData: EnhancedNoteData
): Promise<void> => {
  if (!CONFIG.KNOWLEDGE_GRAPH_ENABLED) return;

  try {
    const graphNode: KnowledgeGraphNode = {
      id: noteData.id || uuidv4(),
      title: noteData.title,
      type: noteData.type || 'note',
      connections: noteData.connections || [],
      metadata: {
        confidence_score: noteData.confidence_score,
        tags: noteData.tags,
        created_at: noteData.created_at,
        updated_at: noteData.updated_at,
      },
    };

    await axios.post(
      `${CONFIG.MCP_SERVER_URL}/knowledge-graph/update`,
      graphNode
    );
  } catch (error) {
    console.warn('Knowledge graph update failed:', error);
  }
};

// API Routes

// Enhanced health check
app.get('/health', (req: Request, res: Response) => {
  const requestId = req.headers['x-request-id'] as string;
  res.json(
    createApiResponse(
      true,
      {
        status: 'healthy',
        version: '3.0.0',
        timestamp: new Date().toISOString(),
        vault_path: CONFIG.VAULT_PATH,
        mcp_server: CONFIG.MCP_SERVER_URL,
        features: {
          real_time_sync: !!fileWatcher,
          auto_tagging: CONFIG.AUTO_TAG_ENABLED,
          knowledge_graph: CONFIG.KNOWLEDGE_GRAPH_ENABLED,
          file_watching: true,
        },
      },
      null,
      requestId
    )
  );
});

// Enhanced note creation with auto-tagging and knowledge graph integration
app.post(
  '/api/notes',
  async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const requestId = req.headers['x-request-id'] as string;
      const noteData: EnhancedNoteData = req.body;

      // Validation
      if (!noteData.title || !noteData.content) {
        throw new Error('Title and content are required');
      }

      // Generate auto-tags if enabled
      if (
        CONFIG.AUTO_TAG_ENABLED &&
        (!noteData.tags || noteData.tags.length === 0)
      ) {
        noteData.tags = await generateAutoTags(
          noteData.content,
          noteData.title
        );
      }

      // Create enhanced frontmatter
      const frontmatter = createEnhancedFrontmatter(noteData);

      // Generate filename
      const timestamp = new Date().toISOString().split('T')[0];
      const filename = `${timestamp}-${sanitizeFilename(noteData.title)}.md`;

      // Determine folder
      const folder = getFolderPath(noteData.type || 'note', frontmatter.status);
      const filepath = path.join(CONFIG.VAULT_PATH, folder, filename);

      // Create note content
      const noteContent = matter.stringify(noteData.content, frontmatter);

      // Ensure directory exists
      await fs.mkdir(path.dirname(filepath), { recursive: true });

      // Write file
      await fs.writeFile(filepath, noteContent, 'utf8');

      // Update knowledge graph
      await updateKnowledgeGraph(noteData);

      // Send to MCP server for processing
      try {
        const mcpPayload = {
          pake_id: frontmatter.pake_id,
          content: noteData.title + '\n\n' + noteData.content,
          confidence_score: frontmatter.confidence_score,
          metadata: {
            title: noteData.title,
            folder,
            filename,
            created_via: 'enhanced_bridge_api',
            auto_tags: noteData.tags,
          },
          type: noteData.type,
          status: frontmatter.status,
          verification_status: frontmatter.verification_status,
          source_uri: frontmatter.source_uri,
          tags: frontmatter.tags,
          connections: frontmatter.connections,
        };

        await axios.post(`${CONFIG.MCP_SERVER_URL}/ingest`, mcpPayload);
      } catch (mcpError) {
        console.warn(
          'Failed to send to MCP server:',
          (mcpError as Error).message
        );
      }

      res.status(201).json(
        createApiResponse(
          true,
          {
            pake_id: frontmatter.pake_id,
            filepath: path.relative(CONFIG.VAULT_PATH, filepath),
            folder,
            filename,
            auto_tags: noteData.tags,
          },
          null,
          requestId
        )
      );
    } catch (error) {
      next(error);
    }
  }
);

// Enhanced search with ML-powered semantic search
app.post(
  '/api/search',
  async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const requestId = req.headers['x-request-id'] as string;
      const {
        query,
        sources = ['web', 'arxiv', 'pubmed'],
        maxResults = 20,
        semantic = true,
      } = req.body;

      if (!query || query.trim().length === 0) {
        throw new Error('Search query is required');
      }

      console.log(
        `[ENHANCED SEARCH] Starting multi-source search for: ${query}`
      );
      const startTime = Date.now();

      // Enhanced MCP server search with semantic capabilities
      try {
        const searchPayload = {
          query: query.trim(),
          limit: parseInt(maxResults),
          confidence_threshold: 0.0,
          semantic_search: semantic,
          sources: sources,
          include_vault_search: true,
          vault_path: CONFIG.VAULT_PATH,
        };

        const mcpResponse = await axios.post(
          `${CONFIG.MCP_SERVER_URL}/search`,
          searchPayload
        );

        if (mcpResponse.data && mcpResponse.data.results) {
          const processingTime = Date.now() - startTime;
          console.log(
            `[ENHANCED SEARCH] MCP search completed in ${processingTime}ms`
          );

          res.json(
            createApiResponse(
              true,
              {
                query: query.trim(),
                results: mcpResponse.data.results.map((result: unknown) => ({
                  id:
                    result.id ||
                    Date.now().toString() + Math.random().toString(36),
                  title: result.title || 'Untitled',
                  content: result.content || result.description || '',
                  source: result.source || 'web',
                  url: result.url || result.source_url,
                  authors: result.authors || [],
                  publishedDate: result.published_date || result.date,
                  confidence: result.confidence || result.quality_score,
                  metadata: result.metadata || {},
                  semantic_score: result.semantic_score || 0,
                })),
                metrics: {
                  totalResults: mcpResponse.data.results.length,
                  processingTime,
                  sourcesQueried: sources.length,
                  semanticEnabled: semantic,
                },
              },
              null,
              requestId
            )
          );
          return;
        }
      } catch (mcpError) {
        console.warn(
          '[ENHANCED SEARCH] MCP server not available, using fallback search'
        );
      }

      // Fallback: Enhanced demo results
      const demoResults = [
        {
          id: '1',
          title: `Enhanced Research Results for: ${query}`,
          content: `This is an enhanced demo result showing how the multi-source research pipeline with semantic search would work. The system searched across ${sources.join(', ')} for relevant information about "${query}".`,
          source: 'web',
          url: 'https://example.com/research',
          confidence: 0.85,
          semantic_score: 0.92,
          metadata: { demo: true, enhanced: true },
        },
        {
          id: '2',
          title: `Academic Paper: ${query} Analysis`,
          content: `Academic research paper discussing various aspects of ${query}. This would typically come from ArXiv or similar academic databases with enhanced semantic matching.`,
          source: 'arxiv',
          url: 'https://arxiv.org/abs/demo',
          authors: ['Dr. Research', 'Prof. Science'],
          publishedDate: new Date().toISOString(),
          confidence: 0.92,
          semantic_score: 0.88,
          metadata: { demo: true, type: 'academic', enhanced: true },
        },
      ].filter(result => sources.includes(result.source));

      const processingTime = Date.now() - startTime;
      console.log(
        `[ENHANCED SEARCH] Demo search completed in ${processingTime}ms`
      );

      res.json(
        createApiResponse(
          true,
          {
            query: query.trim(),
            results: demoResults,
            metrics: {
              totalResults: demoResults.length,
              processingTime,
              sourcesQueried: sources.length,
              semanticEnabled: semantic,
            },
            note: 'Enhanced demo results - connect MCP server for live data',
          },
          null,
          requestId
        )
      );
    } catch (error) {
      next(error);
    }
  }
);

// Real-time sync status endpoint
app.get('/api/sync/status', (req: Request, res: Response) => {
  const requestId = req.headers['x-request-id'] as string;
  res.json(
    createApiResponse(
      true,
      {
        enabled: !!fileWatcher,
        vault_path: CONFIG.VAULT_PATH,
        last_sync: new Date().toISOString(),
        features: {
          file_watching: !!fileWatcher,
          auto_tagging: CONFIG.AUTO_TAG_ENABLED,
          knowledge_graph: CONFIG.KNOWLEDGE_GRAPH_ENABLED,
        },
      },
      null,
      requestId
    )
  );
});

// Knowledge graph integration endpoint
app.get(
  '/api/knowledge-graph',
  async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const requestId = req.headers['x-request-id'] as string;

      if (!CONFIG.KNOWLEDGE_GRAPH_ENABLED) {
        res.json(
          createApiResponse(
            true,
            {
              enabled: false,
              message: 'Knowledge graph integration is disabled',
            },
            null,
            requestId
          )
        );
        return;
      }

      try {
        const response = await axios.get(
          `${CONFIG.MCP_SERVER_URL}/knowledge-graph`
        );
        res.json(createApiResponse(true, response.data, null, requestId));
      } catch (error) {
        res.json(
          createApiResponse(
            true,
            {
              enabled: true,
              error: 'Knowledge graph service unavailable',
              fallback: 'Using local vault analysis',
            },
            null,
            requestId
          )
        );
      }
    } catch (error) {
      next(error);
    }
  }
);

// Enhanced metadata extraction endpoint
app.post(
  '/api/metadata/extract',
  async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const requestId = req.headers['x-request-id'] as string;
      const { content, title } = req.body;

      if (!content) {
        throw new Error('Content is required for metadata extraction');
      }

      try {
        const response = await axios.post(
          `${CONFIG.MCP_SERVER_URL}/ml/extract-metadata`,
          {
            content: title ? title + '\n\n' + content : content,
            include_entities: true,
            include_topics: true,
            include_sentiment: true,
          }
        );

        res.json(createApiResponse(true, response.data, null, requestId));
      } catch (error) {
        // Fallback to basic extraction
        const basicMetadata = {
          word_count: content.split(/\s+/).length,
          character_count: content.length,
          estimated_reading_time: Math.ceil(content.split(/\s+/).length / 200),
          extracted_at: new Date().toISOString(),
        };

        res.json(createApiResponse(true, basicMetadata, null, requestId));
      }
    } catch (error) {
      next(error);
    }
  }
);

// Apply error handling middleware
app.use(errorHandler);

// 404 handler
app.use('*', (req: Request, res: Response) => {
  const requestId = req.headers['x-request-id'] as string;
  res
    .status(404)
    .json(
      createApiResponse(
        false,
        null,
        `Endpoint not found: ${req.method} ${req.originalUrl}`,
        requestId
      )
    );
});

// Graceful shutdown handling
const gracefulShutdown = (signal: string) => {
  console.log(`${signal} received, shutting down gracefully`);

  if (fileWatcher) {
    fileWatcher.close();
  }

  process.exit(0);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Initialize enhanced features
const initializeEnhancedFeatures = async (): Promise<void> => {
  try {
    // Initialize file watcher
    initializeFileWatcher();

    // Test MCP server connection
    try {
      await axios.get(`${CONFIG.MCP_SERVER_URL}/health`);
      console.log('✅ MCP Server connection verified');
    } catch (error) {
      console.warn('⚠️ MCP Server not available, running in standalone mode');
    }

    console.log('🚀 Enhanced Obsidian Bridge v3.0 initialized successfully');
  } catch (error) {
    console.error('❌ Failed to initialize enhanced features:', error);
  }
};

// Start server
const server = app.listen(CONFIG.PORT, async () => {
  console.log(
    `🚀 PAKE+ Enhanced Obsidian Bridge API v3.0 running on port ${CONFIG.PORT}`
  );
  console.log(`📁 Vault path: ${CONFIG.VAULT_PATH}`);
  console.log(`🔗 MCP Server: ${CONFIG.MCP_SERVER_URL}`);
  console.log(`⚡ Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(
    `🏷️ Auto-tagging: ${CONFIG.AUTO_TAG_ENABLED ? 'enabled' : 'disabled'}`
  );
  console.log(
    `🕸️ Knowledge Graph: ${CONFIG.KNOWLEDGE_GRAPH_ENABLED ? 'enabled' : 'disabled'}`
  );

  await initializeEnhancedFeatures();
});

export default app;
