#!/usr/bin/env node
/**
 * PAKE+ Obsidian Bridge API - TypeScript Enhanced Version
 *
 * RESTful API bridge for Obsidian integration with enhanced type safety,
 * error handling, and logging based on monorepo improvements.
 */

import express, { Request, Response, NextFunction, Express } from 'express';
import cors from 'cors';
import { promises as fs } from 'fs';
import path from 'path';
import matter from 'gray-matter';
import { v4 as uuidv4 } from 'uuid';
import axios from 'axios';

// Type definitions for better type safety
interface NoteData {
  id?: string;
  title: string;
  content: string;
  type?: string;
  tags?: string[];
  confidence_score?: number;
  source?: string;
  created_at?: string;
  updated_at?: string;
}

interface FrontmatterData {
  id: string;
  title: string;
  created: string;
  updated: string;
  type: string;
  tags: string[];
  confidence_score: number;
  source: string;
  version: string;
}

interface ApiResponse<T = any> {
  success: boolean;
  data: T | null;
  error: string | null;
  timestamp: string;
}

// Configuration with environment variable support
const CONFIG = {
  PORT: parseInt(process.env.BRIDGE_PORT || '3000'),
  VAULT_PATH: process.env.VAULT_PATH || 'D:\\Knowledge-Vault',
  MCP_SERVER_URL: process.env.MCP_SERVER_URL || 'http://localhost:8000',
  MAX_FILE_SIZE: '50mb',
  LOG_LEVEL: process.env.LOG_LEVEL || 'info',
};

const app: Express = express();

// Enhanced middleware with error handling
app.use(
  cors({
    origin: process.env.ALLOWED_ORIGINS?.split(',') || '*',
    credentials: true,
  })
);

app.use(express.json({ limit: CONFIG.MAX_FILE_SIZE }));
app.use(express.urlencoded({ extended: true }));

// Enhanced logging middleware
app.use((req: Request, res: Response, next: NextFunction) => {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${req.method} ${req.path}`);

  // Add request ID for tracing
  req.headers['x-request-id'] = req.headers['x-request-id'] || uuidv4();
  res.setHeader('x-request-id', req.headers['x-request-id'] as string);

  next();
});

// Utility functions with enhanced error handling
const getCurrentTimestamp = (): string => {
  return new Date().toISOString().replace('T', ' ').replace(/\..+/, '');
};

const createFrontmatter = (data: Partial<NoteData>): FrontmatterData => {
  const timestamp = getCurrentTimestamp();
  return {
    id: data.id || uuidv4(),
    title: data.title || 'Untitled Note',
    created: data.created_at || timestamp,
    updated: data.updated_at || timestamp,
    type: data.type || 'note',
    tags: data.tags || [],
    confidence_score: data.confidence_score || 0.5,
    source: data.source || 'api',
    version: '2.0',
  };
};

const createApiResponse = <T>(
  success: boolean,
  data: T | null = null,
  error: string | null = null
): ApiResponse<T> => {
  return {
    success,
    data,
    error,
    timestamp: new Date().toISOString(),
  };
};

// Enhanced error handling middleware
const errorHandler = (
  error: Error,
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  const requestId = req.headers['x-request-id'] as string;
  console.error(
    `[${new Date().toISOString()}] Error in ${req.method} ${req.path} (${requestId}):`,
    error
  );

  if (res.headersSent) {
    next(error);
    return;
  }

  const statusCode = error instanceof Error && error.name === 'ValidationError' ? 400 : 500;
  const message = error instanceof Error ? error.message : 'An unknown error occurred';
  res.status(statusCode).json(createApiResponse(false, null, message));
};

// API Routes with enhanced error handling and validation
app.get('/api/health', (req: Request, res: Response) => {
  res.json(
    createApiResponse(true, {
      status: 'healthy',
      version: '2.0.0',
      timestamp: new Date().toISOString(),
      vault_path: CONFIG.VAULT_PATH,
    })
  );
});

app.post(
  '/api/notes',
  async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const noteData: NoteData = req.body;

      // Basic validation
      if (!noteData.title || !noteData.content) {
        throw new Error('Title and content are required');
      }

      const frontmatter = createFrontmatter(noteData);
      const filename = `${frontmatter.id}.md`;

      // Determine target directory based on type
      const targetDir = noteData.type === 'inbox' ? '00-Inbox' : '02-Permanent';
      const filePath = path.join(CONFIG.VAULT_PATH, targetDir, filename);

      // Create the note content with frontmatter
      const noteContent = matter.stringify(noteData.content, frontmatter);

      // Ensure directory exists
      await fs.mkdir(path.dirname(filePath), { recursive: true });

      // Write the file
      await fs.writeFile(filePath, noteContent, 'utf8');

      console.log(`Created note: ${filename} in ${targetDir}`);

      res.json(
        createApiResponse(true, {
          id: frontmatter.id,
          filename,
          path: filePath,
          created: frontmatter.created,
        })
      );
    } catch (error) {
      next(error);
    }
  }
);

app.get(
  '/api/notes/:id',
  async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const { id } = req.params;

      // Search for the note in different directories
      const searchDirs = [
        '00-Inbox',
        '01-Daily',
        '02-Permanent',
        '03-Projects',
        '04-Areas',
        '05-Resources',
      ];
      let foundNote: unknown = null;

      for (const dir of searchDirs) {
        const filePath = path.join(CONFIG.VAULT_PATH, dir, `${id}.md`);
        try {
          const content = await fs.readFile(filePath, 'utf8');
          const parsed = matter(content);
          foundNote = {
            id,
            path: filePath,
            frontmatter: parsed.data,
            content: parsed.content,
          };
          break;
        } catch (error) {
          // File not found in this directory, continue searching
          continue;
        }
      }

      if (!foundNote) {
        res
          .status(404)
          .json(createApiResponse(false, null, `Note with id ${id} not found`));
        return;
      }

      res.json(createApiResponse(true, foundNote));
    } catch (error) {
      next(error);
    }
  }
);

// Integration with MCP server (forwarding requests)
app.post(
  '/api/mcp/:endpoint',
  async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const { endpoint } = req.params;
      const mcpUrl = `${CONFIG.MCP_SERVER_URL}/${endpoint}`;

      const response = await axios.post(mcpUrl, req.body, {
        headers: {
          'Content-Type': 'application/json',
          'x-request-id': req.headers['x-request-id'] as string,
        },
        timeout: 30000,
      });

      res.json(createApiResponse(true, response.data));
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status || 500;
        const message = error.response?.data?.error || (error instanceof Error ? error.message : 'An unknown error occurred');
        res
          .status(status)
          .json(createApiResponse(false, null, `MCP Server Error: ${message}`));
      } else {
        next(error);
      }
    }
  }
);

// Apply error handling middleware
app.use(errorHandler);

// 404 handler
app.use('*', (req: Request, res: Response) => {
  res
    .status(404)
    .json(
      createApiResponse(
        false,
        null,
        `Endpoint not found: ${req.method} ${req.originalUrl}`
      )
    );
});

// Graceful shutdown handling
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully');
  process.exit(0);
});

// Start server
const server = app.listen(CONFIG.PORT, () => {
  console.log(
    `🚀 PAKE+ Obsidian Bridge API v2.0 running on port ${CONFIG.PORT}`
  );
  console.log(`📁 Vault path: ${CONFIG.VAULT_PATH}`);
  console.log(`🔗 MCP Server: ${CONFIG.MCP_SERVER_URL}`);
  console.log(`⚡ Environment: ${process.env.NODE_ENV || 'development'}`);
});

export default app;
