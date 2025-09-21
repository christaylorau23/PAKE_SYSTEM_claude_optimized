# PAKE System API Reference

**Version**: 10.1.0  
**Base URL**: `http://localhost:8000` (Development)  
**Documentation**: This document provides comprehensive API reference for the PAKE (Personal AI Knowledge Engine) System.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Endpoints](#endpoints)
  - [System Endpoints](#system-endpoints)
  - [Search Endpoints](#search-endpoints)
  - [ML Intelligence Endpoints](#ml-intelligence-endpoints)
  - [Analytics Endpoints](#analytics-endpoints)
  - [Knowledge Graph Endpoints](#knowledge-graph-endpoints)
  - [Semantic Search Endpoints](#semantic-search-endpoints)
  - [NLP Endpoints](#nlp-endpoints)
- [Data Models](#data-models)
- [Examples](#examples)
- [SDK Examples](#sdk-examples)

## Overview

The PAKE System API provides comprehensive research and knowledge management capabilities through a RESTful interface. The system combines multiple data sources, advanced analytics, and machine learning to deliver intelligent research assistance.

### Key Features

- **Multi-source Research**: Search across web, academic papers, and biomedical literature
- **Semantic Search**: AI-powered semantic understanding and similarity matching
- **Content Summarization**: Advanced text summarization with multiple techniques
- **Knowledge Graph**: Entity relationship mapping and visualization
- **Real-time Analytics**: Comprehensive system metrics and performance monitoring
- **Predictive Analytics**: Trend analysis and forecasting capabilities

## Authentication

Currently running in development mode without authentication. Production deployment will include JWT-based authentication.

```http
Authorization: Bearer <jwt_token>
```

## Rate Limiting

- **Development**: No rate limiting
- **Production**: 1000 requests/hour per API key (planned)

## Error Handling

All API responses follow a consistent error format:

```json
{
  "success": false,
  "error": "error_code",
  "message": "Human-readable error message",
  "timestamp": "2025-09-14T09:25:22.710535",
  "details": {
    "field": "additional_error_details"
  }
}
```

### Common HTTP Status Codes

- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized (planned)
- `403` - Forbidden (planned)
- `404` - Not Found
- `429` - Too Many Requests (planned)
- `500` - Internal Server Error
- `503` - Service Unavailable

## Endpoints

### System Endpoints

#### GET /

Returns basic system information and available endpoints.

**Response:**
```json
{
  "message": "PAKE System API v10.1.0",
  "version": "10.1.0",
  "endpoints": [
    "/search",
    "/ml/dashboard",
    "/analytics"
  ]
}
```

#### GET /health

Returns system health status and component information.

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "version": "10.1.0",
  "timestamp": "2025-09-14T09:25:22.710535",
  "components": {
    "orchestrator": "healthy",
    "firecrawl_api": "demo_mode",
    "arxiv_api": "available",
    "pubmed_api": "available",
    "neo4j_graph_db": "healthy"
  },
  "capabilities": [
    "Multi-source research",
    "Real-time web scraping",
    "Academic paper search",
    "Biomedical literature search",
    "Intelligent deduplication",
    "ML intelligence dashboard",
    "Knowledge graph visualization",
    "Entity relationship mapping"
  ]
}
```

### Search Endpoints

#### POST /search

Performs comprehensive search across multiple sources with optional ML enhancement.

**Request Body:**
```json
{
  "query": "artificial intelligence trends 2025",
  "sources": ["web", "arxiv", "pubmed"],
  "max_results": 10,
  "enable_ml_enhancement": true,
  "enable_content_summarization": false
}
```

**Parameters:**
- `query` (string, required): Search query (1-500 characters)
- `sources` (array, optional): Data sources to search. Options: `["web", "arxiv", "pubmed"]`
- `max_results` (integer, optional): Maximum results (1-50, default: 10)
- `enable_ml_enhancement` (boolean, optional): Enable semantic search (default: true)
- `enable_content_summarization` (boolean, optional): Enable summarization (default: false)

**Response:**
```json
{
  "success": true,
  "query": "artificial intelligence trends 2025",
  "results": [
    {
      "title": "AI Trends Report 2025",
      "url": "https://example.com/ai-trends-2025",
      "snippet": "Comprehensive analysis of AI trends...",
      "source": "web",
      "published_date": "2025-01-15T10:30:00Z",
      "relevance_score": 0.95,
      "semantic_score": 0.88,
      "summary": "Key trends include...",
      "key_points": [
        "Generative AI adoption accelerating",
        "Edge AI becoming mainstream"
      ],
      "entities": [
        {
          "id": "ai_entity_1",
          "name": "Artificial Intelligence",
          "type": "Technology",
          "confidence": 0.92
        }
      ]
    }
  ],
  "total_results": 15,
  "processing_time_ms": 1250.5,
  "ml_enhancement": {
    "semantic_score": 0.88,
    "confidence": 0.92,
    "insights": [
      "Strong focus on practical AI applications",
      "Growing interest in AI ethics"
    ]
  }
}
```

#### POST /quick

Performs a quick search with default settings.

**Request Body:**
```json
{
  "query": "machine learning algorithms",
  "enable_ml_enhancement": true,
  "enable_content_summarization": false
}
```

### ML Intelligence Endpoints

#### POST /summarize

Advanced content summarization using multiple techniques.

**Request Body:**
```json
{
  "content": "Long article content here...",
  "content_type": "academic",
  "target_sentences": 3,
  "include_key_points": true
}
```

**Parameters:**
- `content` (string, required): Content to summarize
- `content_type` (string, optional): Type of content. Options: `["academic", "web", "medical", "general"]`
- `target_sentences` (integer, optional): Number of sentences (1-10, default: 3)
- `include_key_points` (boolean, optional): Include key points (default: true)

**Response:**
```json
{
  "success": true,
  "original_length": 2500,
  "summary_length": 150,
  "compression_ratio": 0.06,
  "extractive_summary": "Key findings include...",
  "abstractive_summary": "The research demonstrates...",
  "key_points": [
    "Point 1: Important finding",
    "Point 2: Key insight"
  ],
  "topics": ["machine learning", "algorithms", "optimization"],
  "sentiment": {
    "score": 0.75,
    "label": "positive"
  },
  "processing_time_ms": 450.2
}
```

#### GET /ml/dashboard

Returns comprehensive ML intelligence dashboard data.

**Response:**
```json
{
  "success": true,
  "dashboard_data": {
    "dashboard_metrics": {
      "total_searches_today": 45,
      "avg_response_time_ms": 1250.5,
      "success_rate": 98.5,
      "active_research_sessions": 12,
      "research_productivity_score": 0.85,
      "exploration_diversity": 0.72,
      "total_content_analyzed": 1250,
      "avg_confidence_score": 0.88,
      "trending_topics": [
        ["artificial intelligence", 15],
        ["machine learning", 12],
        ["data science", 8]
      ],
      "knowledge_gaps": [
        "Quantum computing applications",
        "Edge AI optimization"
      ],
      "focus_areas": [
        "AI Ethics",
        "Neural Architecture Search"
      ]
    },
    "system_status": {
      "patterns_identified": 25,
      "insights_generated": 18
    },
    "knowledge_insights": [
      {
        "title": "Growing Interest in AI Ethics",
        "description": "Recent searches show increased focus on ethical AI development",
        "priority": "high",
        "actionable_suggestions": [
          "Explore AI bias mitigation techniques",
          "Research explainable AI methods"
        ]
      }
    ],
    "recent_sessions": [
      {
        "session_id": "sess_12345",
        "start_time": "2025-09-14T08:30:00Z",
        "total_results": 25,
        "avg_semantic_score": 0.85,
        "dominant_topics": ["AI", "Machine Learning"],
        "queries": [
          "AI trends 2025",
          "machine learning algorithms"
        ]
      }
    ]
  }
}
```

#### GET /ml/insights

Returns AI-generated insights and recommendations.

#### GET /ml/patterns

Returns analysis of research patterns and trends.

#### GET /ml/metrics

Returns ML dashboard metrics and performance data.

#### GET /ml/knowledge-graph

Returns knowledge graph data for visualization.

### Analytics Endpoints

#### GET /analytics/enhanced-dashboard

Returns comprehensive analytics dashboard data.

**Parameters:**
- `time_range` (string, optional): Time range. Options: `["1h", "6h", "24h", "7d", "30d"]`
- `metric_types` (string, optional): Metric types. Options: `["all", "performance", "usage", "system"]`

#### GET /analytics/time-series

Returns time series data for specific metrics.

**Parameters:**
- `metric` (string, optional): Metric name (default: "search_queries")
- `time_range` (string, optional): Time range (default: "24h")
- `granularity` (string, optional): Data granularity. Options: `["minute", "hour", "day", "week"]`

#### GET /analytics/correlations

Returns correlation analysis between metrics.

**Parameters:**
- `metrics` (string, optional): Comma-separated metrics (default: "search_queries,response_time,success_rate,cache_hits")

#### GET /analytics/real-time-activity

Returns real-time system activity data.

#### GET /analytics/comprehensive-report

Returns comprehensive analytics report with predictions and recommendations.

**Parameters:**
- `time_range` (string, optional): Time range (default: "24h")
- `include_predictions` (boolean, optional): Include predictions (default: true)
- `include_recommendations` (boolean, optional): Include recommendations (default: true)

#### GET /analytics/system-health

Returns detailed system health analysis.

#### GET /analytics/insights

Returns analytics insights and recommendations.

**Parameters:**
- `time_range` (string, optional): Time range (default: "24h")
- `priority` (string, optional): Priority filter. Options: `["all", "critical", "high", "medium", "low"]`

#### GET /analytics/anomalies

Returns detected anomalies and alerts.

#### GET /analytics/usage-patterns

Returns usage pattern analysis.

### Knowledge Graph Endpoints

#### POST /graph/entities

Creates a new entity in the knowledge graph.

#### POST /graph/relationships

Creates a relationship between entities.

#### GET /graph/entities/{entity_id}

Retrieves entity information.

#### GET /graph/entities/{entity_id}/relationships

Retrieves relationships for an entity.

#### GET /graph/search

Searches entities in the knowledge graph.

#### GET /graph/visualize

Returns graph visualization data.

#### POST /graph/process-document

Processes a document to extract entities and relationships.

#### GET /graph/stats

Returns knowledge graph statistics.

#### GET /graph/insights/{entity_id}

Returns insights for a specific entity.

### Semantic Search Endpoints

#### POST /semantic/add-documents

Adds documents to the semantic search index.

#### GET /semantic/search

Performs semantic search.

#### GET /semantic/similar/{document_id}

Finds similar documents.

#### GET /semantic/analytics

Returns semantic search analytics.

#### POST /semantic/cluster

Clusters documents semantically.

### NLP Endpoints

#### POST /nlp/extract-entities

Extracts entities from text.

#### POST /nlp/analyze-text

Performs comprehensive text analysis.

## Data Models

### SearchResult

```json
{
  "title": "string",
  "url": "string",
  "snippet": "string",
  "source": "string",
  "published_date": "2025-09-14T09:25:22.710535",
  "relevance_score": 0.95,
  "semantic_score": 0.88,
  "summary": "string",
  "key_points": ["string"],
  "entities": [
    {
      "id": "string",
      "name": "string",
      "type": "string",
      "confidence": 0.92,
      "properties": {}
    }
  ]
}
```

### Entity

```json
{
  "id": "string",
  "name": "string",
  "type": "string",
  "confidence": 0.92,
  "properties": {
    "description": "string",
    "url": "string",
    "created_at": "2025-09-14T09:25:22.710535"
  }
}
```

### KnowledgeInsight

```json
{
  "title": "string",
  "description": "string",
  "priority": "high|medium|low",
  "actionable_suggestions": ["string"]
}
```

## Examples

### Basic Search

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence trends",
    "sources": ["web", "arxiv"],
    "max_results": 5,
    "enable_ml_enhancement": true
  }'
```

### Content Summarization

```bash
curl -X POST "http://localhost:8000/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Your long article content here...",
    "content_type": "academic",
    "target_sentences": 3,
    "include_key_points": true
  }'
```

### ML Dashboard

```bash
curl -X GET "http://localhost:8000/ml/dashboard"
```

### Analytics Report

```bash
curl -X GET "http://localhost:8000/analytics/comprehensive-report?time_range=24h&include_predictions=true"
```

## SDK Examples

### Python

```python
import requests
import json

class PAKEClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def search(self, query, sources=None, max_results=10, enable_ml=True):
        """Perform a search query"""
        payload = {
            "query": query,
            "sources": sources or ["web", "arxiv", "pubmed"],
            "max_results": max_results,
            "enable_ml_enhancement": enable_ml
        }
        
        response = self.session.post(
            f"{self.base_url}/search",
            json=payload
        )
        return response.json()
    
    def summarize(self, content, content_type="general"):
        """Summarize content"""
        payload = {
            "content": content,
            "content_type": content_type,
            "include_key_points": True
        }
        
        response = self.session.post(
            f"{self.base_url}/summarize",
            json=payload
        )
        return response.json()
    
    def get_dashboard(self):
        """Get ML intelligence dashboard"""
        response = self.session.get(f"{self.base_url}/ml/dashboard")
        return response.json()
    
    def get_analytics_report(self, time_range="24h"):
        """Get comprehensive analytics report"""
        params = {"time_range": time_range, "include_predictions": True}
        response = self.session.get(
            f"{self.base_url}/analytics/comprehensive-report",
            params=params
        )
        return response.json()

# Usage example
client = PAKEClient()

# Search
results = client.search("machine learning algorithms")
print(f"Found {results['total_results']} results")

# Summarize
summary = client.summarize("Your long article content...")
print(f"Summary: {summary['extractive_summary']}")

# Dashboard
dashboard = client.get_dashboard()
print(f"Active sessions: {dashboard['dashboard_data']['dashboard_metrics']['active_research_sessions']}")
```

### JavaScript/Node.js

```javascript
class PAKEClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async search(query, options = {}) {
        const payload = {
            query,
            sources: options.sources || ['web', 'arxiv', 'pubmed'],
            max_results: options.maxResults || 10,
            enable_ml_enhancement: options.enableML !== false
        };
        
        const response = await fetch(`${this.baseUrl}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        return response.json();
    }
    
    async summarize(content, contentType = 'general') {
        const payload = {
            content,
            content_type: contentType,
            include_key_points: true
        };
        
        const response = await fetch(`${this.baseUrl}/summarize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        return response.json();
    }
    
    async getDashboard() {
        const response = await fetch(`${this.baseUrl}/ml/dashboard`);
        return response.json();
    }
    
    async getAnalyticsReport(timeRange = '24h') {
        const params = new URLSearchParams({
            time_range: timeRange,
            include_predictions: 'true'
        });
        
        const response = await fetch(
            `${this.baseUrl}/analytics/comprehensive-report?${params}`
        );
        
        return response.json();
    }
}

// Usage example
const client = new PAKEClient();

// Search
const results = await client.search('artificial intelligence trends');
console.log(`Found ${results.total_results} results`);

// Summarize
const summary = await client.summarize('Your long article content...');
console.log(`Summary: ${summary.extractive_summary}`);

// Dashboard
const dashboard = await client.getDashboard();
console.log(`Active sessions: ${dashboard.dashboard_data.dashboard_metrics.active_research_sessions}`);
```

### cURL Examples

```bash
# Health check
curl -X GET "http://localhost:8000/health"

# Search with ML enhancement
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "quantum computing applications",
    "sources": ["web", "arxiv"],
    "max_results": 10,
    "enable_ml_enhancement": true,
    "enable_content_summarization": true
  }'

# Quick search
curl -X POST "http://localhost:8000/quick" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning algorithms"
  }'

# Summarize content
curl -X POST "http://localhost:8000/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Your article content here...",
    "content_type": "academic",
    "target_sentences": 3
  }'

# Get ML dashboard
curl -X GET "http://localhost:8000/ml/dashboard"

# Get analytics report
curl -X GET "http://localhost:8000/analytics/comprehensive-report?time_range=7d"

# Get system health
curl -X GET "http://localhost:8000/analytics/system-health?time_range=24h"

# Semantic search
curl -X GET "http://localhost:8000/semantic/search?q=machine%20learning&top_k=10"

# Knowledge graph visualization
curl -X GET "http://localhost:8000/graph/visualize?max_nodes=50"
```

## Webhook Support (Planned)

Future versions will include webhook support for real-time notifications:

- Search completion notifications
- Anomaly detection alerts
- System health status changes
- New insights generation

## Rate Limiting Details (Planned)

- **Free Tier**: 100 requests/hour
- **Pro Tier**: 1000 requests/hour
- **Enterprise**: Custom limits

Rate limit headers will be included in responses:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Support

For API support and questions:

- **Documentation**: [https://docs.pake-system.com](https://docs.pake-system.com)
- **GitHub Issues**: [https://github.com/pake-system/issues](https://github.com/pake-system/issues)
- **Email**: api-support@pake-system.com

## Changelog

### Version 10.1.0 (Current)
- Added ML Intelligence Dashboard
- Enhanced analytics capabilities
- Improved semantic search
- Added knowledge graph visualization
- Comprehensive API documentation

### Version 10.0.0
- Initial release
- Multi-source search
- Basic analytics
- Content summarization