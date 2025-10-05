#!/bin/bash

# PAKE System Orchestrator - Test Runner
# Comprehensive test suite execution with coverage reporting

set -e

echo "🚀 PAKE System Orchestrator - Test Suite"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}Error: Must be run from orchestrator service directory${NC}"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}📦 Installing dependencies...${NC}"
    npm install
fi

echo ""
echo -e "${BLUE}🔧 Building TypeScript...${NC}"
npm run build

echo ""
echo -e "${BLUE}🧹 Running linter...${NC}"
npm run lint

echo ""
echo -e "${BLUE}✨ Checking code formatting...${NC}"
npm run format:check

echo ""
echo -e "${BLUE}📋 Validating JSON schemas...${NC}"
npm run validate-schemas

echo ""
echo -e "${BLUE}🧪 Running unit tests...${NC}"
npm run test:unit

echo ""
echo -e "${BLUE}🔗 Running integration tests...${NC}"
npm run test:integration

echo ""
echo -e "${BLUE}📊 Running full test suite with coverage...${NC}"
npm run test:coverage

echo ""
echo -e "${BLUE}🔍 Security audit...${NC}"
npm run audit-security

echo ""
echo -e "${GREEN}✅ All tests passed successfully!${NC}"
echo ""
echo -e "${YELLOW}📈 Coverage Report:${NC}"
echo "View detailed coverage: ./coverage/lcov-report/index.html"
echo ""
echo -e "${YELLOW}🎯 Key Test Results:${NC}"
echo "• Unit Tests: Provider routing, circuit breakers, metrics"
echo "• Integration Tests: Full API flow, mocked providers, error handling"
echo "• Contract Tests: JSON schema validation, provider interfaces"
echo ""
echo -e "${GREEN}🎉 Phase B Implementation Complete!${NC}"
