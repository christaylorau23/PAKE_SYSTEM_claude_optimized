#!/bin/bash

echo "🔍 Checking Graphiti MCP Server Status"
echo "======================================"

# Check if containers are running
echo "📦 Docker Containers:"
docker ps --filter "name=graphiti" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""

# Check MCP server health
echo "🏥 MCP Server Health:"
if curl -sf http://localhost:8000/health; then
    echo "✅ MCP Server is healthy"
else
    echo "❌ MCP Server is not responding"
fi

echo ""

# Check Neo4j connectivity
echo "🔗 Neo4j Connection:"
if curl -sf http://localhost:7474; then
    echo "✅ Neo4j Browser accessible"
else
    echo "❌ Neo4j Browser not accessible"
fi

echo ""

# Check for active connections/sessions
echo "📊 MCP Server Stats:"
curl -sf http://localhost:8000/stats 2>/dev/null || echo "Stats endpoint not available"

echo ""

# Check recent knowledge graph activity
echo "🧠 Knowledge Graph Activity:"
curl -sf http://localhost:8000/episodes/recent 2>/dev/null || echo "Episodes endpoint not available"

echo ""
echo "🔧 Troubleshooting:"
echo "- If containers aren't running: ./setup-graphiti.sh"
echo "- If health checks fail: docker-compose -f graphiti-standalone.yml logs"
echo "- View Neo4j data: http://localhost:7474 (neo4j/graphiti_REDACTED_SECRET)"