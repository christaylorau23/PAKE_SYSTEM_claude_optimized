import fs from 'fs/promises';
import path from 'path';
import chokidar from 'chokidar';
import matter from 'gray-matter';
import MarkdownIt from 'markdown-it';
import { logger } from '../utils/logger.js';

class KnowledgeService {
  constructor() {
    this.knowledgeVaultPath =
      process.env.KNOWLEDGE_VAULT_PATH || 'D:/Knowledge-Vault';
    this.pakeSystemPath =
      process.env.PAKE_SYSTEM_PATH || 'D:/Knowledge-Vault/01-PAKE-System';
    this.knowledgeCache = new Map();
    this.fileWatcher = null;
    this.md = new MarkdownIt({
      html: true,
      linkify: true,
      typographer: true,
    });

    this.initializeWatcher();
    this.loadKnowledgeBase();
  }

  async initializeWatcher() {
    try {
      // Watch for changes in markdown files
      this.fileWatcher = chokidar.watch('**/*.md', {
        cwd: this.knowledgeVaultPath,
        ignored: /node_modules|\.git/,
        persistent: true,
        ignoreInitial: true,
      });

      this.fileWatcher
        .on('add', filePath => this.handleFileChange('add', filePath))
        .on('change', filePath => this.handleFileChange('change', filePath))
        .on('unlink', filePath => this.handleFileChange('delete', filePath))
        .on('error', error => {
          logger.error('File watcher error:', error);
        });

      logger.info(`📁 Watching knowledge vault at: ${this.knowledgeVaultPath}`);
    } catch (error) {
      logger.error('Failed to initialize file watcher:', error);
    }
  }

  async handleFileChange(event, filePath) {
    try {
      const fullPath = path.join(this.knowledgeVaultPath, filePath);
      const cacheKey = this.getCacheKey(fullPath);

      switch (event) {
        case 'add':
        case 'change':
          await this.loadFileToCache(fullPath, cacheKey);
          logger.debug(`📄 ${event}: ${filePath}`);
          break;
        case 'delete':
          this.knowledgeCache.delete(cacheKey);
          logger.debug(`🗑️ Removed from cache: ${filePath}`);
          break;
      }
    } catch (error) {
      logger.error(`Error handling file ${event} for ${filePath}:`, error);
    }
  }

  async loadKnowledgeBase() {
    try {
      logger.info('📚 Loading knowledge base...');
      const startTime = Date.now();

      const files = await this.findMarkdownFiles(this.knowledgeVaultPath);

      for (const filePath of files) {
        const cacheKey = this.getCacheKey(filePath);
        await this.loadFileToCache(filePath, cacheKey);
      }

      const loadTime = Date.now() - startTime;
      logger.info(`✅ Loaded ${files.length} documents in ${loadTime}ms`);
    } catch (error) {
      logger.error('Failed to load knowledge base:', error);
    }
  }

  async findMarkdownFiles(dir) {
    const files = [];

    try {
      const entries = await fs.readdir(dir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);

        if (entry.isDirectory() && !entry.name.startsWith('.')) {
          const subFiles = await this.findMarkdownFiles(fullPath);
          files.push(...subFiles);
        } else if (entry.isFile() && entry.name.endsWith('.md')) {
          files.push(fullPath);
        }
      }
    } catch (error) {
      logger.warn(`Cannot read directory ${dir}:`, error.message);
    }

    return files;
  }

  async loadFileToCache(filePath, cacheKey) {
    try {
      const content = await fs.readFile(filePath, 'utf-8');
      const parsed = matter(content);
      const stats = await fs.stat(filePath);

      const document = {
        id: cacheKey,
        filePath: filePath,
        relativePath: path.relative(this.knowledgeVaultPath, filePath),
        title:
          parsed.data.title ||
          this.extractTitleFromContent(parsed.content) ||
          path.basename(filePath, '.md'),
        content: parsed.content,
        html: this.md.render(parsed.content),
        frontmatter: parsed.data,
        tags: parsed.data.tags || [],
        category: this.categorizeDocument(filePath),
        wordCount: parsed.content.split(/\s+/).length,
        createdAt: stats.birthtime,
        modifiedAt: stats.mtime,
        size: stats.size,
      };

      this.knowledgeCache.set(cacheKey, document);
      return document;
    } catch (error) {
      logger.error(`Failed to load file ${filePath}:`, error);
      return null;
    }
  }

  extractTitleFromContent(content) {
    const lines = content.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('# ')) {
        return trimmed.substring(2).trim();
      }
    }
    return null;
  }

  categorizeDocument(filePath) {
    const relativePath = path.relative(this.knowledgeVaultPath, filePath);
    const parts = relativePath.split(path.sep);

    if (parts[0] === '01-PAKE-System') {
      return parts[1] || 'PAKE-System';
    }

    return parts[0] || 'General';
  }

  getCacheKey(filePath) {
    return path.relative(this.knowledgeVaultPath, filePath).replace(/\\/g, '/');
  }

  // Public API methods
  async getAllDocuments(options = {}) {
    const { category, tags, limit, offset = 0 } = options;
    let documents = Array.from(this.knowledgeCache.values());

    // Filter by category
    if (category) {
      documents = documents.filter(doc => doc.category === category);
    }

    // Filter by tags
    if (tags && tags.length > 0) {
      documents = documents.filter(doc =>
        tags.some(tag => doc.tags.includes(tag))
      );
    }

    // Sort by modification date (newest first)
    documents.sort((a, b) => new Date(b.modifiedAt) - new Date(a.modifiedAt));

    // Apply pagination
    const total = documents.length;
    if (limit) {
      documents = documents.slice(offset, offset + limit);
    }

    return {
      documents,
      total,
      offset,
      limit: limit || total,
    };
  }

  async getDocumentById(id) {
    return this.knowledgeCache.get(id) || null;
  }

  async getDocumentsByCategory(category) {
    const documents = Array.from(this.knowledgeCache.values()).filter(
      doc => doc.category === category
    );

    return documents.sort(
      (a, b) => new Date(b.modifiedAt) - new Date(a.modifiedAt)
    );
  }

  async getCategories() {
    const categories = new Set();
    this.knowledgeCache.forEach(doc => {
      categories.add(doc.category);
    });

    return Array.from(categories).sort();
  }

  async getTags() {
    const tagCounts = new Map();

    this.knowledgeCache.forEach(doc => {
      doc.tags.forEach(tag => {
        tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
      });
    });

    return Array.from(tagCounts.entries())
      .map(([tag, count]) => ({ tag, count }))
      .sort((a, b) => b.count - a.count);
  }

  async getKnowledgeStats() {
    const documents = Array.from(this.knowledgeCache.values());
    const categories = new Set();
    const tags = new Set();
    let totalWords = 0;

    documents.forEach(doc => {
      categories.add(doc.category);
      doc.tags.forEach(tag => tags.add(tag));
      totalWords += doc.wordCount;
    });

    return {
      totalDocuments: documents.length,
      totalCategories: categories.size,
      totalTags: tags.size,
      totalWords,
      lastUpdated: new Date().toISOString(),
    };
  }

  // Cleanup method
  destroy() {
    if (this.fileWatcher) {
      this.fileWatcher.close();
      logger.info('📁 File watcher closed');
    }
  }
}

export const knowledgeService = new KnowledgeService();
