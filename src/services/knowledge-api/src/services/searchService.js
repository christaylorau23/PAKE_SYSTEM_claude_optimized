import Fuse from 'fuse.js';
import { logger } from '../utils/logger.js';
import { knowledgeService } from './knowledgeService.js';

class SearchService {
  constructor() {
    this.searchIndex = null;
    this.fuseOptions = {
      includeScore: true,
      includeMatches: true,
      threshold: parseFloat(process.env.SEARCH_FUZZY_THRESHOLD) || 0.3,
      minMatchCharLength: 2,
      keys: [
        {
          name: 'title',
          weight: 0.4,
        },
        {
          name: 'content',
          weight: 0.3,
        },
        {
          name: 'tags',
          weight: 0.2,
        },
        {
          name: 'category',
          weight: 0.1,
        },
      ],
    };

    this.initializeSearchIndex();
  }

  async initializeSearchIndex() {
    try {
      logger.info('🔍 Initializing search index...');
      await this.rebuildSearchIndex();
      logger.info('✅ Search index initialized');
    } catch (error) {
      logger.error('Failed to initialize search index:', error);
    }
  }

  async rebuildSearchIndex() {
    try {
      const { documents } = await knowledgeService.getAllDocuments();
      this.searchIndex = new Fuse(documents, this.fuseOptions);
      logger.debug(
        `🔍 Search index rebuilt with ${documents.length} documents`
      );
    } catch (error) {
      logger.error('Failed to rebuild search index:', error);
      throw error;
    }
  }

  async search(query, options = {}) {
    const startTime = Date.now();

    try {
      if (!this.searchIndex) {
        await this.rebuildSearchIndex();
      }

      const {
        limit = parseInt(process.env.MAX_SEARCH_RESULTS) || 50,
        category,
        tags,
        includeContent = false,
      } = options;

      if (!query || query.trim().length === 0) {
        return {
          results: [],
          total: 0,
          query: query,
          searchTime: 0,
        };
      }

      // Perform fuzzy search
      let searchResults = this.searchIndex.search(query);

      // Filter by category if specified
      if (category) {
        searchResults = searchResults.filter(
          result => result.item.category === category
        );
      }

      // Filter by tags if specified
      if (tags && tags.length > 0) {
        searchResults = searchResults.filter(result =>
          tags.some(tag => result.item.tags.includes(tag))
        );
      }

      // Limit results
      const total = searchResults.length;
      searchResults = searchResults.slice(0, limit);

      // Format results
      const results = searchResults.map(result => {
        const formattedResult = {
          id: result.item.id,
          title: result.item.title,
          category: result.item.category,
          tags: result.item.tags,
          relativePath: result.item.relativePath,
          score: Math.round((1 - result.score) * 100), // Convert to percentage relevance
          modifiedAt: result.item.modifiedAt,
          wordCount: result.item.wordCount,
        };

        // Include content preview if requested
        if (includeContent) {
          formattedResult.contentPreview = this.generateContentPreview(
            result.item.content,
            query,
            200
          );
          formattedResult.matches = this.formatMatches(result.matches);
        }

        return formattedResult;
      });

      const searchTime = Date.now() - startTime;

      logger.info(
        `🔍 Search completed: "${query}" - ${results.length}/${total} results in ${searchTime}ms`
      );

      return {
        results,
        total,
        query: query,
        searchTime,
        options: {
          limit,
          category,
          tags,
          includeContent,
        },
      };
    } catch (error) {
      logger.error(`Search failed for query "${query}":`, error);
      throw error;
    }
  }

  async searchByCategory(category, query = '', options = {}) {
    return this.search(query, { ...options, category });
  }

  async searchByTags(tags, query = '', options = {}) {
    if (typeof tags === 'string') {
      tags = [tags];
    }
    return this.search(query, { ...options, tags });
  }

  async getSuggestions(partialQuery, limit = 10) {
    try {
      if (!partialQuery || partialQuery.length < 2) {
        return [];
      }

      const { documents } = await knowledgeService.getAllDocuments();
      const suggestions = new Set();

      // Search in titles
      documents.forEach(doc => {
        if (doc.title.toLowerCase().includes(partialQuery.toLowerCase())) {
          suggestions.add(doc.title);
        }

        // Search in tags
        doc.tags.forEach(tag => {
          if (tag.toLowerCase().includes(partialQuery.toLowerCase())) {
            suggestions.add(tag);
          }
        });
      });

      // Search for common phrases in content (simple word extraction)
      const words = partialQuery.toLowerCase().split(/\s+/);
      const lastWord = words[words.length - 1];

      if (lastWord.length >= 3) {
        documents.forEach(doc => {
          const contentWords =
            doc.content.toLowerCase().match(/\b\w{3,}\b/g) || [];
          contentWords.forEach(word => {
            if (word.startsWith(lastWord) && word.length > lastWord.length) {
              const suggestion = words.slice(0, -1).join(' ') + ' ' + word;
              suggestions.add(suggestion.trim());
            }
          });
        });
      }

      return Array.from(suggestions).slice(0, limit);
    } catch (error) {
      logger.error(`Failed to get suggestions for "${partialQuery}":`, error);
      return [];
    }
  }

  generateContentPreview(content, query, maxLength = 200) {
    if (!content || !query) {
      return content ? content.substring(0, maxLength) + '...' : '';
    }

    const queryLower = query.toLowerCase();
    const contentLower = content.toLowerCase();

    // Find the best match position
    const matchIndex = contentLower.indexOf(queryLower);

    if (matchIndex === -1) {
      // No direct match, return beginning
      return (
        content.substring(0, maxLength) +
        (content.length > maxLength ? '...' : '')
      );
    }

    // Calculate preview window around the match
    const start = Math.max(0, matchIndex - Math.floor(maxLength / 3));
    const end = Math.min(content.length, start + maxLength);

    let preview = content.substring(start, end);

    // Add ellipsis if we're not at the beginning/end
    if (start > 0) preview = '...' + preview;
    if (end < content.length) preview = preview + '...';

    return preview;
  }

  formatMatches(matches) {
    if (!matches) return [];

    return matches.map(match => ({
      key: match.key,
      value: match.value,
      indices: match.indices,
    }));
  }

  async getSearchStats() {
    try {
      const stats = await knowledgeService.getKnowledgeStats();
      return {
        ...stats,
        searchIndexStatus: this.searchIndex ? 'ready' : 'building',
        fuseOptions: {
          threshold: this.fuseOptions.threshold,
          keys: this.fuseOptions.keys.map(key =>
            typeof key === 'string' ? key : key.name
          ),
        },
      };
    } catch (error) {
      logger.error('Failed to get search stats:', error);
      throw error;
    }
  }

  // Force refresh of search index
  async refreshIndex() {
    try {
      await this.rebuildSearchIndex();
      return { success: true, message: 'Search index refreshed successfully' };
    } catch (error) {
      logger.error('Failed to refresh search index:', error);
      throw error;
    }
  }
}

export const searchService = new SearchService();
