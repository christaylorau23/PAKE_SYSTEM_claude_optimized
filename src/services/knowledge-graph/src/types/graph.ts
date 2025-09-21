// Knowledge Graph Type Definitions
// Aligned with Neo4j schema and multi-modal processing pipeline

// Core Node Types
export interface BaseNode {
  id: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface GraphNode extends BaseNode {
  labels: string[];
  properties: Record<string, unknown>;
  type: string;
  name: string;
  updatedAt?: Date;
}

export interface Document extends BaseNode {
  title: string;
  content: string;
  filePath?: string;
  contentType?: string;
  size?: number;
  metadata?: Record<string, any>;
}

export interface Entity extends BaseNode {
  name: string;
  type: EntityType;
  confidence: number;
  source: string;
  properties?: Record<string, any>;
}

export interface Concept extends BaseNode {
  name: string;
  description?: string;
  category?: string;
  importance: number;
  occurrences: number;
  relatedConcepts: string[];
}

export interface User extends BaseNode {
  username: string;
  email: string;
  preferences?: Record<string, any>;
  activity?: UserActivity[];
}

export interface Query extends BaseNode {
  text: string;
  userId: string;
  results?: string[];
  feedback?: QueryFeedback;
}

// Relationship Types
export interface GraphRelationship {
  id: string;
  type: string;
  source: string;
  target: string;
  properties?: Record<string, any>;
  weight?: number;
  confidence?: number;
  createdAt: Date;
}

// Entity Types
export type EntityType =
  | 'PERSON'
  | 'ORGANIZATION'
  | 'LOCATION'
  | 'DATE'
  | 'TIME'
  | 'MONEY'
  | 'PERCENTAGE'
  | 'EMAIL'
  | 'URL'
  | 'PHONE'
  | 'TECHNOLOGY'
  | 'CONCEPT'
  | 'OBJECT'
  | 'SCENE';

// Processing Types
export interface ProcessingResult {
  documentId: string;
  entities: Entity[];
  relationships: GraphRelationship[];
  concepts: Concept[];
  processingTime: number;
  timestamp: Date;
}

export interface BatchProcessingResult {
  results: ProcessingResult[];
  totalProcessingTime: number;
  successCount: number;
  errorCount: number;
  errors: ProcessingError[];
}

export interface ProcessingError {
  documentId: string;
  error: string;
  timestamp: Date;
}

// Update Types
export interface GraphUpdate {
  type: 'create' | 'update' | 'delete';
  nodeType: string;
  nodeId: string;
  properties?: Record<string, any>;
  relationships?: GraphRelationship[];
  timestamp: Date;
}

export interface BatchGraphUpdate {
  updates: GraphUpdate[];
  batchId: string;
  timestamp: Date;
}

// User Activity
export interface UserActivity {
  type: 'search' | 'view' | 'create' | 'update' | 'delete';
  target: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface QueryFeedback {
  rating: number;
  helpful: boolean;
  comments?: string;
}

// Reasoning and Analysis Types
export interface GraphPath {
  nodes: GraphNode[];
  relationships: GraphRelationship[];
  length: number;
  weight: number;
  confidence: number;
}

export interface GraphCluster {
  id: string;
  nodes: string[];
  centrality: number;
  density: number;
  topics: string[];
}

export interface GraphInsight {
  id: string;
  type: 'anomaly' | 'pattern' | 'trend' | 'recommendation';
  title: string;
  description: string;
  confidence: number;
  evidence: unknown[];
  createdAt: Date;
}

export interface KnowledgeGap {
  id: string;
  description: string;
  missingConnections: Array<{
    source: string;
    target: string;
    expectedRelation: string;
  }>;
  priority: number;
}

export interface QueryPattern {
  pattern: string;
  frequency: number;
  avgResponseTime: number;
  successRate: number;
  relatedTopics: string[];
}

export interface EntityImportance {
  entityId: string;
  score: number;
  centrality: number;
  frequency: number;
  recentActivity: number;
}

export interface ConceptHierarchy {
  rootConcept: string;
  children: ConceptHierarchy[];
  strength: number;
  examples: string[];
}

// Graph Statistics
export interface GraphStatistics {
  totalNodes: number;
  totalRelationships: number;
  nodeTypes: Record<string, number>;
  relationshipTypes: Record<string, number>;
  averageDegree: number;
  density: number;
  lastUpdated: string;
}

export interface GraphMetrics {
  processingTime: number;
  nodesProcessed: number;
  relationshipsCreated: number;
  entitiesExtracted: number;
  timestamp: Date;
}

// Search and Recommendation Types
export interface SearchQuery {
  text: string;
  filters?: SearchFilters;
  limit?: number;
}

export interface SearchFilters {
  nodeTypes?: string[];
  dateRange?: {
    from?: string;
    to?: string;
  };
  properties?: Record<string, any>;
}

export interface SearchResult {
  node: GraphNode;
  score: number;
  matchType: 'exact' | 'text' | 'fuzzy' | 'semantic' | 'contextual';
  snippet: string;
}

export interface Recommendation {
  node: GraphNode;
  score: number;
  reason: string;
  type: 'similarity' | 'connected' | 'popular' | 'personalized' | 'trending';
}
