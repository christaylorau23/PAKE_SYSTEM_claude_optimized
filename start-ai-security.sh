#!/bin/bash

# Start AI Security Monitoring System
# This script launches the complete AI security monitoring stack

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "========================================"
echo "  AI Security Monitoring System"
echo "========================================"
echo -e "${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose.${NC}"
    exit 1
fi

# Set Docker Compose command
COMPOSE_CMD="docker-compose"
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
fi

echo -e "${BLUE}🔍 Starting AI Security Monitoring Components...${NC}"
echo ""

# Check what services to start
PROFILE="security-monitoring"
if [[ "$1" == "full" ]]; then
    PROFILE="full"
    echo -e "${YELLOW}📋 Starting full security monitoring stack (ELK + AI + Dashboard)${NC}"
elif [[ "$1" == "ai-only" ]]; then
    PROFILE="ai-security"
    echo -e "${YELLOW}🤖 Starting AI security monitor only${NC}"
elif [[ "$1" == "elk-only" ]]; then
    PROFILE="elk"
    echo -e "${YELLOW}📊 Starting ELK stack only${NC}"
else
    echo -e "${YELLOW}🛡️ Starting security monitoring stack (default)${NC}"
fi

# Start services
echo -e "${BLUE}🚀 Launching services...${NC}"

$COMPOSE_CMD -f docker/docker-compose.yml -f docker-compose.override.yml \
    --profile $PROFILE up -d

# Wait for services to start
echo -e "${BLUE}⏳ Waiting for services to become healthy...${NC}"

# Function to wait for service health
wait_for_service() {
    local service=$1
    local port=$2
    local timeout=120
    local counter=0

    echo -n "Waiting for $service"
    while ! curl -f -s "http://localhost:$port" > /dev/null 2>&1; do
        if [ $counter -eq $timeout ]; then
            echo -e "\n${RED}❌ Timeout waiting for $service${NC}"
            return 1
        fi
        echo -n "."
        sleep 2
        counter=$((counter + 2))
    done
    echo -e " ${GREEN}✅ Ready${NC}"
}

# Wait for key services
if [[ "$PROFILE" == "full" || "$PROFILE" == "security-monitoring" || "$PROFILE" == "elk" ]]; then
    wait_for_service "Elasticsearch" 9200
    wait_for_service "Kibana" 5601
fi

if [[ "$PROFILE" == "full" || "$PROFILE" == "security-monitoring" || "$PROFILE" == "ai-security" ]]; then
    wait_for_service "AI Security Monitor" 8080
fi

if [[ "$PROFILE" == "full" || "$PROFILE" == "security-monitoring" ]]; then
    wait_for_service "Security Dashboard" 8090
fi

echo ""
echo -e "${GREEN}🎉 AI Security Monitoring System is running!${NC}"
echo ""
echo -e "${BLUE}📋 Access Points:${NC}"

if [[ "$PROFILE" == "full" || "$PROFILE" == "security-monitoring" || "$PROFILE" == "ai-security" ]]; then
    echo -e "🤖 AI Security Monitor API:  ${GREEN}http://localhost:8080${NC}"
    echo -e "📊 API Dashboard:            ${GREEN}http://localhost:8080/dashboard${NC}"
    echo -e "🔍 Health Check:             ${GREEN}http://localhost:8080/health${NC}"
fi

if [[ "$PROFILE" == "full" || "$PROFILE" == "security-monitoring" ]]; then
    echo -e "🌐 Security Dashboard:       ${GREEN}http://localhost:8090${NC}"
fi

if [[ "$PROFILE" == "full" || "$PROFILE" == "security-monitoring" || "$PROFILE" == "elk" ]]; then
    echo -e "📈 Kibana (Log Analytics):   ${GREEN}http://localhost:5601${NC}"
    echo -e "🔎 Elasticsearch:            ${GREEN}http://localhost:9200${NC}"
fi

echo ""
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo -e "View logs:           ${YELLOW}docker logs pake_ai_security_monitor${NC}"
echo -e "Stop services:       ${YELLOW}$COMPOSE_CMD -f docker/docker-compose.yml -f docker-compose.override.yml --profile $PROFILE down${NC}"
echo -e "Restart AI Monitor:  ${YELLOW}docker restart pake_ai_security_monitor${NC}"
echo ""

echo -e "${BLUE}📊 Testing the AI Security Monitor:${NC}"
echo -e "1. Generate test alerts:     ${YELLOW}curl -X POST http://localhost:8080/analyze${NC}"
echo -e "2. View current alerts:      ${YELLOW}curl http://localhost:8080/alerts${NC}"
echo -e "3. Check system health:      ${YELLOW}curl http://localhost:8080/health${NC}"
echo ""

echo -e "${GREEN}✨ Your AI security monitoring system is now protecting your infrastructure!${NC}"
echo -e "${BLUE}The AI will continuously analyze logs for security threats and anomalies.${NC}"

# Optional: Show current status
echo ""
echo -e "${BLUE}📈 Current System Status:${NC}"
if curl -f -s "http://localhost:8080/health" > /dev/null 2>&1; then
    curl -s "http://localhost:8080/health" | python -m json.tool 2>/dev/null || echo "AI Security Monitor: ✅ Active"
else
    echo "AI Security Monitor: ⚠️ Starting up..."
fi