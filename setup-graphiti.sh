#!/bin/bash
set -e

echo "🚀 Setting up Graphiti MCP Server for PAKE System"

# Check dependencies
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed."; exit 1; }

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not found in environment"
    read -p "Enter your OpenAI API key: " api_key
    echo "OPENAI_API_KEY=$api_key" >> .env.graphiti
    echo "✅ API key added to .env.graphiti"
fi

# Start Graphiti MCP services
echo "🐳 Starting Graphiti MCP services..."
docker-compose -f graphiti-standalone.yml --env-file .env.graphiti up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Health check
echo "🏥 Checking service health..."
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✅ Graphiti MCP Server is running at http://localhost:8000"
else
    echo "❌ Graphiti MCP Server health check failed"
    exit 1
fi

if curl -sf http://localhost:7474 > /dev/null; then
    echo "✅ Neo4j Browser available at http://localhost:7474"
    echo "   Username: neo4j"
    echo "   Password: graphiti_REDACTED_SECRET"
else
    echo "⚠️  Neo4j Browser not accessible"
fi

echo ""
echo "🎉 Graphiti MCP Server setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Configure Claude Code with the provided claude-config.json"
echo "2. Configure Cursor IDE with the provided cursor-config.json"
echo "3. Test the connection with: curl http://localhost:8000/health"
echo ""
echo "🔗 Connection endpoints:"
echo "   - MCP Server: http://localhost:8000"
echo "   - SSE Stream: http://localhost:8000/sse"
echo "   - Neo4j Browser: http://localhost:7474"
echo ""