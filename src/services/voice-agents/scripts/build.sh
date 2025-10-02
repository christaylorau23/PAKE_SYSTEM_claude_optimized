#!/bin/bash

# PAKE System Voice Agents - Build Script
# Builds Docker images for production and development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 PAKE Voice Agents - Build Script${NC}"
echo "=================================="

# Default values
BUILD_TYPE="both"
NO_CACHE=""
PLATFORM=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --prod|--production)
      BUILD_TYPE="production"
      shift
      ;;
    --dev|--development)
      BUILD_TYPE="development"
      shift
      ;;
    --no-cache)
      NO_CACHE="--no-cache"
      shift
      ;;
    --platform)
      PLATFORM="--platform $2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  --prod, --production   Build production image only"
      echo "  --dev, --development   Build development image only"
      echo "  --no-cache            Build without using cache"
      echo "  --platform PLATFORM   Set target platform (e.g., linux/amd64)"
      echo "  -h, --help            Show this help message"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Function to build production image
build_production() {
    echo -e "${YELLOW}📦 Building production image...${NC}"

    docker build \
        $NO_CACHE \
        $PLATFORM \
        -f Dockerfile \
        -t pake-system/voice-agents:latest \
        -t pake-system/voice-agents:$(date +%Y%m%d-%H%M%S) \
        .

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Production image built successfully${NC}"
    else
        echo -e "${RED}❌ Production image build failed${NC}"
        exit 1
    fi
}

# Function to build development image
build_development() {
    echo -e "${YELLOW}🔧 Building development image...${NC}"

    docker build \
        $NO_CACHE \
        $PLATFORM \
        -f Dockerfile.dev \
        -t pake-system/voice-agents:dev \
        .

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Development image built successfully${NC}"
    else
        echo -e "${RED}❌ Development image build failed${NC}"
        exit 1
    fi
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Build based on type
case $BUILD_TYPE in
    "production")
        build_production
        ;;
    "development")
        build_development
        ;;
    "both")
        build_production
        echo ""
        build_development
        ;;
esac

echo ""
echo -e "${GREEN}🎉 Build process completed successfully!${NC}"

# Show built images
echo ""
echo -e "${BLUE}📋 Built images:${NC}"
docker images | grep pake-system/voice-agents

echo ""
echo -e "${BLUE}💡 Next steps:${NC}"
echo "  • Run: docker-compose up -d (production)"
echo "  • Run: docker-compose -f docker-compose.dev.yml up -d (development)"
echo "  • Test: curl http://localhost:9000/health"