#!/bin/bash

# PAKE System Voice Agents - Deployment Script
# Handles deployment, health checks, and rollback

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 PAKE Voice Agents - Deployment Script${NC}"
echo "========================================"

# Default values
ENVIRONMENT="production"
HEALTH_CHECK_TIMEOUT=60
ROLLBACK_ON_FAILURE=true
COMPOSE_FILE="docker-compose.yml"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --env|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --dev|--development)
      ENVIRONMENT="development"
      COMPOSE_FILE="docker-compose.dev.yml"
      shift
      ;;
    --timeout)
      HEALTH_CHECK_TIMEOUT="$2"
      shift 2
      ;;
    --no-rollback)
      ROLLBACK_ON_FAILURE=false
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  --env ENVIRONMENT     Set deployment environment (default: production)"
      echo "  --dev, --development  Deploy to development environment"
      echo "  --timeout SECONDS     Health check timeout (default: 60)"
      echo "  --no-rollback        Don't rollback on deployment failure"
      echo "  -h, --help           Show this help message"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Function to check if service is healthy
check_health() {
    local service_name=$1
    local max_attempts=$(($HEALTH_CHECK_TIMEOUT / 5))
    local attempt=0
    
    echo -e "${YELLOW}🔍 Checking health of $service_name...${NC}"
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s http://localhost:9000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is healthy${NC}"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -e "${YELLOW}⏳ Attempt $attempt/$max_attempts - waiting for $service_name...${NC}"
        sleep 5
    done
    
    echo -e "${RED}❌ $service_name health check failed after $HEALTH_CHECK_TIMEOUT seconds${NC}"
    return 1
}

# Function to get current container ID
get_container_id() {
    docker ps -q -f name=pake-voice-agents
}

# Function to rollback deployment
rollback() {
    echo -e "${YELLOW}🔄 Rolling back deployment...${NC}"
    
    # Stop current containers
    docker-compose -f $COMPOSE_FILE down
    
    # Get previous image
    local previous_image=$(docker images pake-system/voice-agents --format "table {{.Tag}}" | grep -E '^[0-9]' | head -2 | tail -1)
    
    if [ -n "$previous_image" ]; then
        echo -e "${YELLOW}📦 Rolling back to image: $previous_image${NC}"
        
        # Update docker-compose to use previous image
        sed -i.bak "s|pake-system/voice-agents:latest|pake-system/voice-agents:$previous_image|g" $COMPOSE_FILE
        
        # Start with previous image
        docker-compose -f $COMPOSE_FILE up -d
        
        # Restore original compose file
        mv ${COMPOSE_FILE}.bak $COMPOSE_FILE
        
        echo -e "${GREEN}✅ Rollback completed${NC}"
    else
        echo -e "${RED}❌ No previous image found for rollback${NC}"
        exit 1
    fi
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if required files exist
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}❌ Docker Compose file not found: $COMPOSE_FILE${NC}"
    exit 1
fi

if [ ! -f ".env.example" ] && [ "$ENVIRONMENT" = "production" ]; then
    echo -e "${YELLOW}⚠️  .env.example not found. Make sure to set environment variables.${NC}"
fi

# Save current container ID for rollback
OLD_CONTAINER_ID=$(get_container_id)

echo -e "${BLUE}📋 Deployment Configuration:${NC}"
echo "  Environment: $ENVIRONMENT"
echo "  Compose file: $COMPOSE_FILE"
echo "  Health check timeout: ${HEALTH_CHECK_TIMEOUT}s"
echo "  Rollback on failure: $ROLLBACK_ON_FAILURE"
echo ""

# Start deployment
echo -e "${YELLOW}🚀 Starting deployment...${NC}"

# Pull latest images (if not building locally)
echo -e "${YELLOW}📥 Pulling latest images...${NC}"
docker-compose -f $COMPOSE_FILE pull || echo -e "${YELLOW}⚠️  Could not pull images (might be using local build)${NC}"

# Stop and remove current containers
echo -e "${YELLOW}🛑 Stopping current services...${NC}"
docker-compose -f $COMPOSE_FILE down --remove-orphans

# Start new containers
echo -e "${YELLOW}🆙 Starting new services...${NC}"
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 10

# Health check
if check_health "voice-agents"; then
    echo -e "${GREEN}🎉 Deployment successful!${NC}"
    
    # Show deployment info
    echo ""
    echo -e "${BLUE}📊 Deployment Info:${NC}"
    echo "  Service URL: http://localhost:9000"
    echo "  Health Check: http://localhost:9000/health"
    echo "  Metrics: http://localhost:9000/metrics"
    echo "  API Docs: http://localhost:9000/docs"
    
    # Show running containers
    echo ""
    echo -e "${BLUE}🐳 Running Containers:${NC}"
    docker-compose -f $COMPOSE_FILE ps
    
    # Show resource usage
    echo ""
    echo -e "${BLUE}💻 Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker-compose -f $COMPOSE_FILE ps -q)
    
else
    echo -e "${RED}❌ Deployment failed - service is not healthy${NC}"
    
    # Show logs for debugging
    echo ""
    echo -e "${BLUE}📋 Recent logs:${NC}"
    docker-compose -f $COMPOSE_FILE logs --tail=50
    
    # Rollback if enabled
    if [ "$ROLLBACK_ON_FAILURE" = true ]; then
        rollback
    else
        echo -e "${YELLOW}⚠️  Rollback disabled. Manual intervention required.${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}✅ Deployment process completed${NC}"