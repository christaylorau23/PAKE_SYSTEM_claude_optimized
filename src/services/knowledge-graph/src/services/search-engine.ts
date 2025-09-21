import { Neo4jService } from './neo4j';
import { GraphManager } from './graph-manager';
import { ReasoningEngine } from './reasoning-engine';
import {
  GraphNode,
  GraphRelationship,
  SearchResult,
  Recommendation,
  SearchQuery,
  SearchFilters,
} from '@/types/graph';
import { logger, searchLogger } from '@/utils/logger';
import natural from 'natural';
import { EventEmitter } from 'events';

interface SearchConfig {
  maxResults: number;
  enableFuzzySearch: boolean;
  fuzzyThreshold: number;
  enableSemanticSearch: boolean;
  boostFactors: {
    exactMatch: number;
    titleMatch: number;
    contentMatch: number;
    typeMatch: number;
    recentness: number;
    popularity: number;
  };
  caching: {
    enabled: boolean;
    ttl: number; // Time to live in milliseconds
    maxCacheSize: number;
  };
}

interface SearchIndex {
  nodeId: string;
  content: string;
  tokens: string[];
  tfidf: number[];
  type: string;
  lastUpdated: Date;
}

interface RecommendationContext {
  userId?: string;
  sessionId?: string;
  currentNodeId?: string;
  recentActivity: string[];
  preferences: Record<string, number>;
  excludeTypes?: string[];
}

interface CachedResult {
  data: any;
  timestamp: number;
  ttl: number;
}

export class SearchEngine extends EventEmitter {
  private neo4jService: Neo4jService;
  private graphManager: GraphManager;
  private reasoningEngine: ReasoningEngine;
  private config: SearchConfig;
  private searchIndex: Map<string, SearchIndex> = new Map();
  private tfidfVectorizer: any;
  private cache: Map<string, CachedResult> = new Map();
  private isInitialized = false;

  constructor(
    neo4jService: Neo4jService,
    graphManager: GraphManager,
    reasoningEngine: ReasoningEngine,
    config: Partial<SearchConfig> = {}
  ) {
    super();
    this.neo4jService = neo4jService;
    this.graphManager = graphManager;
    this.reasoningEngine = reasoningEngine;

    this.config = {
      maxResults: 50,
      enableFuzzySearch: true,
      fuzzyThreshold: 0.7,
      enableSemanticSearch: true,
      boostFactors: {
        exactMatch: 2.0,
        titleMatch: 1.8,
        contentMatch: 1.0,
        typeMatch: 1.5,
        recentness: 0.3,
        popularity: 0.5,
      },
      caching: {
        enabled: true,
        ttl: 300000, // 5 minutes
        maxCacheSize: 1000,
      },
      ...config,
    };

    this.setupPeriodicCacheCleanup();
  }

  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      searchLogger.info('Initializing Search Engine...');

      // Build search index
      await this.buildSearchIndex();

      // Initialize TF-IDF vectorizer
      this.initializeTfidfVectorizer();

      // Setup event listeners for index updates
      this.setupEventListeners();

      this.isInitialized = true;
      searchLogger.info('Search Engine initialized successfully');
      this.emit('initialized');
    } catch (error) {
      searchLogger.error('Failed to initialize Search Engine:', error);
      throw error;
    }
  }

  private async buildSearchIndex(): Promise<void> {
    searchLogger.info('Building search index...');

    const query = `
      MATCH (n)
      RETURN n.id as id, 
             labels(n) as labels,
             n.name as name,
             n.title as title,
             n.content as content,
             n.description as description,
             n.updatedAt as updatedAt
      LIMIT 10000
    `;

    const result = await this.neo4jService.executeQuery(query);

    for (const record of result.records) {
      const nodeData = record.toObject();
      await this.indexNode({
        id: nodeData.id,
        name: nodeData.name,
        title: nodeData.title,
        content: nodeData.content,
        description: nodeData.description,
        type: nodeData.labels?.[0] || 'Unknown',
        updatedAt: nodeData.updatedAt
          ? new Date(nodeData.updatedAt)
          : new Date(),
      });
    }

    searchLogger.info(`Search index built with ${this.searchIndex.size} nodes`);
  }

  private async indexNode(node: any): Promise<void> {
    const content = [node.name, node.title, node.content, node.description]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();

    if (!content.trim()) return;

    const tokens = natural.WordTokenizer.tokenize(content) || [];
    const stemmedTokens = tokens.map(token =>
      natural.PorterStemmer.stem(token)
    );

    const searchIndex: SearchIndex = {
      nodeId: node.id,
      content,
      tokens: stemmedTokens,
      tfidf: [], // Will be calculated after all nodes are indexed
      type: node.type,
      lastUpdated: node.updatedAt || new Date(),
    };

    this.searchIndex.set(node.id, searchIndex);
  }

  private initializeTfidfVectorizer(): void {
    // Calculate TF-IDF vectors for all indexed content
    const documents = Array.from(this.searchIndex.values()).map(
      index => index.content
    );

    if (documents.length === 0) return;

    const tfidf = natural.TfIdf;
    const vectorizer = new tfidf();

    documents.forEach(doc => vectorizer.addDocument(doc));

    // Update search index with TF-IDF vectors
    Array.from(this.searchIndex.values()).forEach((index, docIndex) => {
      const vector: number[] = [];
      vectorizer.listTerms(docIndex).forEach(item => {
        vector.push(item.tfidf);
      });
      index.tfidf = vector;
    });

    this.tfidfVectorizer = vectorizer;
    searchLogger.info('TF-IDF vectorizer initialized');
  }

  private setupEventListeners(): void {
    this.graphManager.on('node_created', node => {
      this.indexNode(node).catch(error => {
        searchLogger.error('Failed to index new node:', error);
      });
    });

    this.graphManager.on('node_updated', node => {
      this.indexNode(node).catch(error => {
        searchLogger.error('Failed to reindex updated node:', error);
      });
    });

    this.graphManager.on('node_deleted', nodeId => {
      this.searchIndex.delete(nodeId);
      this.invalidateCache();
    });
  }

  private setupPeriodicCacheCleanup(): void {
    setInterval(() => {
      this.cleanupCache();
    }, 60000); // Clean up every minute
  }

  async search(
    query: SearchQuery,
    filters?: SearchFilters
  ): Promise<SearchResult[]> {
    if (!this.isInitialized) {
      throw new Error('Search Engine not initialized');
    }

    const cacheKey = this.getCacheKey('search', { query, filters });
    const cached = this.getFromCache(cacheKey);
    if (cached) {
      return cached as SearchResult[];
    }

    try {
      const startTime = Date.now();

      // Normalize query
      const normalizedQuery = query.text.toLowerCase().trim();
      const queryTokens = natural.WordTokenizer.tokenize(normalizedQuery) || [];
      const stemmedQueryTokens = queryTokens.map(token =>
        natural.PorterStemmer.stem(token)
      );

      // Perform different types of searches
      const results: SearchResult[] = [];

      // 1. Exact matches
      const exactMatches = await this.findExactMatches(
        normalizedQuery,
        filters
      );
      results.push(
        ...exactMatches.map(r => ({
          ...r,
          score: r.score * this.config.boostFactors.exactMatch,
        }))
      );

      // 2. Full-text search
      const textMatches = await this.findTextMatches(
        stemmedQueryTokens,
        filters
      );
      results.push(...textMatches);

      // 3. Fuzzy search (if enabled)
      if (this.config.enableFuzzySearch) {
        const fuzzyMatches = await this.findFuzzyMatches(
          normalizedQuery,
          filters
        );
        results.push(...fuzzyMatches);
      }

      // 4. Semantic search (if enabled)
      if (this.config.enableSemanticSearch) {
        const semanticMatches = await this.findSemanticMatches(
          normalizedQuery,
          filters
        );
        results.push(...semanticMatches);
      }

      // 5. Graph-based contextual search
      const contextualMatches = await this.findContextualMatches(
        normalizedQuery,
        filters
      );
      results.push(...contextualMatches);

      // Deduplicate and sort results
      const uniqueResults = this.deduplicateResults(results);
      const sortedResults = this.rankResults(uniqueResults, normalizedQuery);
      const finalResults = sortedResults.slice(0, this.config.maxResults);

      // Cache results
      this.setCache(cacheKey, finalResults);

      const executionTime = Date.now() - startTime;
      searchLogger.info(
        `Search completed in ${executionTime}ms, found ${finalResults.length} results`
      );

      this.emit('search_completed', {
        query: normalizedQuery,
        resultCount: finalResults.length,
        executionTime,
      });

      return finalResults;
    } catch (error) {
      searchLogger.error('Search failed:', error);
      throw error;
    }
  }

  private async findExactMatches(
    query: string,
    filters?: SearchFilters
  ): Promise<SearchResult[]> {
    const cypher = `
      MATCH (n)
      WHERE toLower(n.name) CONTAINS $query 
         OR toLower(n.title) CONTAINS $query
         OR toLower(n.description) CONTAINS $query
         ${this.buildFilterClause(filters)}
      RETURN n, 
             CASE 
               WHEN toLower(n.name) = $query THEN 1.0
               WHEN toLower(n.title) = $query THEN 0.9
               WHEN toLower(n.name) STARTS WITH $query THEN 0.8
               WHEN toLower(n.title) STARTS WITH $query THEN 0.7
               ELSE 0.6
             END as score
      ORDER BY score DESC
      LIMIT 20
    `;

    const result = await this.neo4jService.executeQuery(cypher, {
      query,
      ...filters,
    });

    return result.records.map(record => ({
      node: this.recordToNode(record.get('n')),
      score: record.get('score'),
      matchType: 'exact',
      snippet: this.generateSnippet(record.get('n'), query),
    }));
  }

  private async findTextMatches(
    queryTokens: string[],
    filters?: SearchFilters
  ): Promise<SearchResult[]> {
    const results: SearchResult[] = [];

    for (const [nodeId, index] of this.searchIndex) {
      if (filters?.nodeTypes && !filters.nodeTypes.includes(index.type)) {
        continue;
      }

      const matchingTokens = queryTokens.filter(token =>
        index.tokens.includes(token)
      );

      if (matchingTokens.length === 0) continue;

      const score = this.calculateTextScore(queryTokens, index);

      if (score > 0.1) {
        // Minimum threshold
        try {
          const node = await this.getNodeById(nodeId);
          if (node) {
            results.push({
              node,
              score,
              matchType: 'text',
              snippet: this.generateSnippetFromContent(
                index.content,
                queryTokens.join(' ')
              ),
            });
          }
        } catch (error) {
          searchLogger.warn(`Failed to get node ${nodeId}:`, error);
        }
      }
    }

    return results.sort((a, b) => b.score - a.score).slice(0, 30);
  }

  private async findFuzzyMatches(
    query: string,
    filters?: SearchFilters
  ): Promise<SearchResult[]> {
    const results: SearchResult[] = [];

    for (const [nodeId, index] of this.searchIndex) {
      if (filters?.nodeTypes && !filters.nodeTypes.includes(index.type)) {
        continue;
      }

      const distance = natural.JaroWinklerDistance(query, index.content);

      if (distance >= this.config.fuzzyThreshold) {
        try {
          const node = await this.getNodeById(nodeId);
          if (node) {
            results.push({
              node,
              score: distance * 0.8, // Lower weight for fuzzy matches
              matchType: 'fuzzy',
              snippet: this.generateSnippetFromContent(index.content, query),
            });
          }
        } catch (error) {
          searchLogger.warn(`Failed to get node ${nodeId}:`, error);
        }
      }
    }

    return results.sort((a, b) => b.score - a.score).slice(0, 20);
  }

  private async findSemanticMatches(
    query: string,
    filters?: SearchFilters
  ): Promise<SearchResult[]> {
    // For now, use TF-IDF similarity as a proxy for semantic similarity
    // In a production system, you would use embeddings/word2vec/BERT
    const results: SearchResult[] = [];

    if (!this.tfidfVectorizer) return results;

    // Create query vector
    const queryDoc = new natural.TfIdf();
    queryDoc.addDocument(query);

    for (const [nodeId, index] of this.searchIndex) {
      if (filters?.nodeTypes && !filters.nodeTypes.includes(index.type)) {
        continue;
      }

      // Calculate cosine similarity between query and document
      const similarity = this.calculateCosineSimilarity(
        this.getQueryVector(query),
        index.tfidf
      );

      if (similarity > 0.2) {
        try {
          const node = await this.getNodeById(nodeId);
          if (node) {
            results.push({
              node,
              score: similarity * 0.9,
              matchType: 'semantic',
              snippet: this.generateSnippetFromContent(index.content, query),
            });
          }
        } catch (error) {
          searchLogger.warn(`Failed to get node ${nodeId}:`, error);
        }
      }
    }

    return results.sort((a, b) => b.score - a.score).slice(0, 25);
  }

  private async findContextualMatches(
    query: string,
    filters?: SearchFilters
  ): Promise<SearchResult[]> {
    // Use graph structure to find contextually relevant nodes
    const cypher = `
      CALL db.index.fulltext.queryNodes("nodeSearchIndex", $query) YIELD node, score
      MATCH (node)-[r1]-(connected1)-[r2]-(connected2)
      WHERE connected2.name IS NOT NULL
      ${this.buildFilterClause(filters, 'connected2')}
      RETURN DISTINCT connected2 as n, 
             score * 0.3 as contextScore,
             count(DISTINCT r1) + count(DISTINCT r2) as connectionStrength
      ORDER BY contextScore * connectionStrength DESC
      LIMIT 15
    `;

    try {
      const result = await this.neo4jService.executeQuery(cypher, { query });

      return result.records.map(record => ({
        node: this.recordToNode(record.get('n')),
        score: record.get('contextScore') * record.get('connectionStrength'),
        matchType: 'contextual',
        snippet: this.generateSnippet(record.get('n'), query),
      }));
    } catch (error) {
      // Fallback if fulltext index doesn't exist
      searchLogger.warn(
        'Fulltext search failed, using basic contextual search:',
        error
      );
      return [];
    }
  }

  private deduplicateResults(results: SearchResult[]): SearchResult[] {
    const seen = new Set<string>();
    const deduplicated: SearchResult[] = [];

    // Sort by score first to keep best matches
    results.sort((a, b) => b.score - a.score);

    for (const result of results) {
      if (!seen.has(result.node.id)) {
        seen.add(result.node.id);
        deduplicated.push(result);
      }
    }

    return deduplicated;
  }

  private rankResults(results: SearchResult[], query: string): SearchResult[] {
    return results
      .map(result => {
        let adjustedScore = result.score;

        // Apply boost factors
        if (result.matchType === 'exact') {
          adjustedScore *= this.config.boostFactors.exactMatch;
        } else if (result.matchType === 'text') {
          adjustedScore *= this.config.boostFactors.contentMatch;
        }

        // Type-based boosting
        if (result.node.type === 'Document') {
          adjustedScore *= this.config.boostFactors.titleMatch;
        }

        // Recency boost
        if (result.node.updatedAt) {
          const daysSinceUpdate =
            (Date.now() - result.node.updatedAt.getTime()) /
            (1000 * 60 * 60 * 24);
          const recencyBoost =
            Math.exp(-daysSinceUpdate / 30) *
            this.config.boostFactors.recentness;
          adjustedScore += recencyBoost;
        }

        return {
          ...result,
          score: adjustedScore,
        };
      })
      .sort((a, b) => b.score - a.score);
  }

  async getRecommendations(
    nodeId: string,
    context?: RecommendationContext,
    limit: number = 10
  ): Promise<Recommendation[]> {
    const cacheKey = this.getCacheKey('recommendations', {
      nodeId,
      context,
      limit,
    });
    const cached = this.getFromCache(cacheKey);
    if (cached) {
      return cached as Recommendation[];
    }

    try {
      const recommendations: Recommendation[] = [];

      // Get the source node
      const sourceNode = await this.getNodeById(nodeId);
      if (!sourceNode) {
        throw new Error(`Node ${nodeId} not found`);
      }

      // 1. Similar nodes based on relationships
      const similarNodes = await this.reasoningEngine.findSimilarNodes(
        nodeId,
        0.7,
        limit * 2
      );
      recommendations.push(
        ...similarNodes.map(node => ({
          node,
          score: node.similarity,
          reason: 'Similar content or structure',
          type: 'similarity' as const,
        }))
      );

      // 2. Connected nodes with high relevance
      const connectedNodes = await this.findConnectedRecommendations(
        nodeId,
        context
      );
      recommendations.push(...connectedNodes);

      // 3. Popular nodes in the same domain
      const popularNodes = await this.findPopularRecommendations(
        sourceNode.type,
        context
      );
      recommendations.push(...popularNodes);

      // 4. User-specific recommendations (if context provided)
      if (context?.userId || context?.recentActivity) {
        const personalizedNodes = await this.findPersonalizedRecommendations(
          nodeId,
          context
        );
        recommendations.push(...personalizedNodes);
      }

      // 5. Trending nodes
      const trendingNodes = await this.findTrendingRecommendations(
        sourceNode.type,
        limit
      );
      recommendations.push(...trendingNodes);

      // Deduplicate and rank
      const uniqueRecommendations =
        this.deduplicateRecommendations(recommendations);
      const rankedRecommendations = this.rankRecommendations(
        uniqueRecommendations,
        sourceNode,
        context
      );
      const finalRecommendations = rankedRecommendations.slice(0, limit);

      // Cache results
      this.setCache(cacheKey, finalRecommendations);

      searchLogger.info(
        `Generated ${finalRecommendations.length} recommendations for node ${nodeId}`
      );
      return finalRecommendations;
    } catch (error) {
      searchLogger.error('Failed to generate recommendations:', error);
      throw error;
    }
  }

  private async findConnectedRecommendations(
    nodeId: string,
    context?: RecommendationContext
  ): Promise<Recommendation[]> {
    const cypher = `
      MATCH (source {id: $nodeId})-[r1]-(intermediate)-[r2]-(target)
      WHERE source <> target 
        AND NOT (source)-[r2]-(target)
        ${context?.excludeTypes ? 'AND NOT target:' + context.excludeTypes.join(' AND NOT target:') : ''}
      RETURN target,
             count(DISTINCT intermediate) as pathCount,
             collect(DISTINCT type(r1)) + collect(DISTINCT type(r2)) as relationshipTypes,
             avg(r1.weight + r2.weight) as avgWeight
      ORDER BY pathCount * avgWeight DESC
      LIMIT 15
    `;

    const result = await this.neo4jService.executeQuery(cypher, { nodeId });

    return result.records.map(record => ({
      node: this.recordToNode(record.get('target')),
      score: record.get('pathCount') * (record.get('avgWeight') || 1),
      reason: `Connected through ${record.get('pathCount')} intermediate nodes`,
      type: 'connected' as const,
    }));
  }

  private async findPopularRecommendations(
    nodeType: string,
    context?: RecommendationContext
  ): Promise<Recommendation[]> {
    const cypher = `
      MATCH (n:${nodeType})-[r]-()
      WHERE n.id <> $excludeId
        ${context?.excludeTypes ? 'AND NOT n:' + context.excludeTypes.join(' AND NOT n:') : ''}
      RETURN n,
             count(r) as popularity,
             avg(r.weight) as avgWeight
      ORDER BY popularity DESC, avgWeight DESC
      LIMIT 10
    `;

    const result = await this.neo4jService.executeQuery(cypher, {
      excludeId: context?.currentNodeId || '',
    });

    return result.records.map(record => ({
      node: this.recordToNode(record.get('n')),
      score: record.get('popularity') * (record.get('avgWeight') || 1) * 0.3,
      reason: `Popular ${nodeType.toLowerCase()} with ${record.get('popularity')} connections`,
      type: 'popular' as const,
    }));
  }

  private async findPersonalizedRecommendations(
    nodeId: string,
    context: RecommendationContext
  ): Promise<Recommendation[]> {
    // This would integrate with user behavior analytics
    // For now, return recommendations based on recent activity
    const recommendations: Recommendation[] = [];

    if (context.recentActivity && context.recentActivity.length > 0) {
      for (const activityNodeId of context.recentActivity.slice(0, 3)) {
        try {
          const similarToActivity = await this.reasoningEngine.findSimilarNodes(
            activityNodeId,
            0.6,
            5
          );

          recommendations.push(
            ...similarToActivity.map(node => ({
              node,
              score: node.similarity * 0.4, // Lower weight for activity-based
              reason: 'Based on your recent activity',
              type: 'personalized' as const,
            }))
          );
        } catch (error) {
          searchLogger.warn(
            `Failed to get personalized recommendations for activity ${activityNodeId}:`,
            error
          );
        }
      }
    }

    return recommendations;
  }

  private async findTrendingRecommendations(
    nodeType: string,
    limit: number
  ): Promise<Recommendation[]> {
    // Find nodes with recent high activity
    const cypher = `
      MATCH (n:${nodeType})
      WHERE n.createdAt > datetime() - duration('P7D') // Last 7 days
      OPTIONAL MATCH (n)-[r]-()
      WHERE r.createdAt > datetime() - duration('P1D') // Recent relationships
      RETURN n,
             count(r) as recentActivity,
             n.createdAt as createdAt
      ORDER BY recentActivity DESC, createdAt DESC
      LIMIT $limit
    `;

    try {
      const result = await this.neo4jService.executeQuery(cypher, { limit });

      return result.records.map(record => ({
        node: this.recordToNode(record.get('n')),
        score: record.get('recentActivity') * 0.2,
        reason: `Trending ${nodeType.toLowerCase()} with recent activity`,
        type: 'trending' as const,
      }));
    } catch (error) {
      searchLogger.warn('Failed to get trending recommendations:', error);
      return [];
    }
  }

  private deduplicateRecommendations(
    recommendations: Recommendation[]
  ): Recommendation[] {
    const seen = new Set<string>();
    const deduplicated: Recommendation[] = [];

    recommendations.sort((a, b) => b.score - a.score);

    for (const rec of recommendations) {
      if (!seen.has(rec.node.id)) {
        seen.add(rec.node.id);
        deduplicated.push(rec);
      }
    }

    return deduplicated;
  }

  private rankRecommendations(
    recommendations: Recommendation[],
    sourceNode: GraphNode,
    context?: RecommendationContext
  ): Recommendation[] {
    return recommendations
      .map(rec => {
        let adjustedScore = rec.score;

        // Type diversity bonus
        if (rec.node.type !== sourceNode.type) {
          adjustedScore *= 1.1;
        }

        // Context-based adjustments
        if (context?.preferences) {
          const typePreference = context.preferences[rec.node.type] || 0.5;
          adjustedScore *= 0.5 + typePreference;
        }

        // Recency adjustment
        if (rec.node.updatedAt) {
          const hoursOld =
            (Date.now() - rec.node.updatedAt.getTime()) / (1000 * 60 * 60);
          if (hoursOld < 24) {
            adjustedScore *= 1.2; // Boost recent content
          }
        }

        return {
          ...rec,
          score: adjustedScore,
        };
      })
      .sort((a, b) => b.score - a.score);
  }

  // Helper methods
  private calculateTextScore(
    queryTokens: string[],
    index: SearchIndex
  ): number {
    const matches = queryTokens.filter(token => index.tokens.includes(token));
    const termFrequency = matches.length / queryTokens.length;
    const documentFrequency = matches.length / index.tokens.length;
    return (termFrequency + documentFrequency) / 2;
  }

  private calculateCosineSimilarity(vec1: number[], vec2: number[]): number {
    if (vec1.length !== vec2.length) return 0;

    let dotProduct = 0;
    let magnitude1 = 0;
    let magnitude2 = 0;

    for (let i = 0; i < vec1.length; i++) {
      dotProduct += vec1[i] * vec2[i];
      magnitude1 += vec1[i] ** 2;
      magnitude2 += vec2[i] ** 2;
    }

    const magnitude = Math.sqrt(magnitude1) * Math.sqrt(magnitude2);
    return magnitude === 0 ? 0 : dotProduct / magnitude;
  }

  private getQueryVector(query: string): number[] {
    // Simplified query vector generation
    const queryDoc = new natural.TfIdf();
    queryDoc.addDocument(query);
    const vector: number[] = [];
    queryDoc.listTerms(0).forEach(item => {
      vector.push(item.tfidf);
    });
    return vector;
  }

  private buildFilterClause(
    filters?: SearchFilters,
    nodeAlias: string = 'n'
  ): string {
    if (!filters) return '';

    const clauses: string[] = [];

    if (filters.nodeTypes && filters.nodeTypes.length > 0) {
      clauses.push(`${nodeAlias}:${filters.nodeTypes.join(`|${nodeAlias}:`)}`);
    }

    if (filters.dateRange) {
      if (filters.dateRange.from) {
        clauses.push(
          `${nodeAlias}.createdAt >= datetime('${filters.dateRange.from}')`
        );
      }
      if (filters.dateRange.to) {
        clauses.push(
          `${nodeAlias}.createdAt <= datetime('${filters.dateRange.to}')`
        );
      }
    }

    if (filters.properties) {
      Object.entries(filters.properties).forEach(([key, value]) => {
        clauses.push(`${nodeAlias}.${key} = '${value}'`);
      });
    }

    return clauses.length > 0 ? 'AND ' + clauses.join(' AND ') : '';
  }

  private async getNodeById(nodeId: string): Promise<GraphNode | null> {
    try {
      const result = await this.neo4jService.executeQuery(
        'MATCH (n {id: $nodeId}) RETURN n',
        { nodeId }
      );

      if (result.records.length === 0) return null;
      return this.recordToNode(result.records[0].get('n'));
    } catch (error) {
      searchLogger.warn(`Failed to get node ${nodeId}:`, error);
      return null;
    }
  }

  private recordToNode(record: any): GraphNode {
    return {
      id: record.properties.id,
      labels: record.labels,
      properties: record.properties,
      type: record.labels[0],
      name: record.properties.name || record.properties.title || 'Unnamed',
      updatedAt: record.properties.updatedAt
        ? new Date(record.properties.updatedAt)
        : undefined,
    };
  }

  private generateSnippet(node: any, query: string): string {
    const content = [
      node.properties.name,
      node.properties.title,
      node.properties.content,
      node.properties.description,
    ]
      .filter(Boolean)
      .join(' ');

    return this.generateSnippetFromContent(content, query);
  }

  private generateSnippetFromContent(content: string, query: string): string {
    if (!content) return '';

    const queryWords = query.toLowerCase().split(/\s+/);
    const sentences = content.split(/[.!?]+/);

    // Find sentence with most query word matches
    let bestSentence = sentences[0] || '';
    let maxMatches = 0;

    for (const sentence of sentences) {
      const lowerSentence = sentence.toLowerCase();
      const matches = queryWords.filter(word =>
        lowerSentence.includes(word)
      ).length;
      if (matches > maxMatches) {
        maxMatches = matches;
        bestSentence = sentence;
      }
    }

    // Truncate if too long
    if (bestSentence.length > 200) {
      bestSentence = bestSentence.substring(0, 197) + '...';
    }

    return bestSentence.trim();
  }

  // Cache management
  private getCacheKey(operation: string, params: any): string {
    return `${operation}:${JSON.stringify(params)}`;
  }

  private getFromCache(key: string): any | null {
    if (!this.config.caching.enabled) return null;

    const cached = this.cache.get(key);
    if (!cached) return null;

    if (Date.now() > cached.timestamp + cached.ttl) {
      this.cache.delete(key);
      return null;
    }

    return cached.data;
  }

  private setCache(key: string, data: any): void {
    if (!this.config.caching.enabled) return;

    // Implement LRU eviction
    if (this.cache.size >= this.config.caching.maxCacheSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl: this.config.caching.ttl,
    });
  }

  private cleanupCache(): void {
    const now = Date.now();
    for (const [key, cached] of this.cache.entries()) {
      if (now > cached.timestamp + cached.ttl) {
        this.cache.delete(key);
      }
    }
  }

  private invalidateCache(): void {
    this.cache.clear();
  }

  // Public API
  async rebuildIndex(): Promise<void> {
    searchLogger.info('Rebuilding search index...');
    this.searchIndex.clear();
    this.invalidateCache();
    await this.buildSearchIndex();
    this.initializeTfidfVectorizer();
    searchLogger.info('Search index rebuilt successfully');
  }

  getIndexStats(): any {
    return {
      totalNodes: this.searchIndex.size,
      cacheSize: this.cache.size,
      isInitialized: this.isInitialized,
    };
  }

  async stop(): Promise<void> {
    searchLogger.info('Stopping Search Engine...');
    this.searchIndex.clear();
    this.cache.clear();
    this.removeAllListeners();
    searchLogger.info('Search Engine stopped');
  }
}

export default SearchEngine;
