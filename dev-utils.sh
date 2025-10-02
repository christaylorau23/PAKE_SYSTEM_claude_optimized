#!/bin/bash

# 🚀 PAKE System Development Utilities
# Advanced workflow scripts for AI-assisted development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}🚀 PAKE System - $1${NC}"
    echo "----------------------------------------"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Quick system health check
health_check() {
    print_header "System Health Check"

    # Check Python environment
    if python --version > /dev/null 2>&1; then
        print_success "Python: $(python --version)"
    else
        print_error "Python not found"
        return 1
    fi

    # Check Node.js environment
    if node --version > /dev/null 2>&1; then
        print_success "Node.js: $(node --version)"
    else
        print_error "Node.js not found"
        return 1
    fi

    # Check if bridge is running
    if curl -f http://localhost:3001/health > /dev/null 2>&1; then
        print_success "TypeScript Bridge: Running on port 3001"
    else
        print_warning "TypeScript Bridge: Not running"
    fi

    # Check environment file
    if [ -f ".env" ]; then
        print_success "Environment file: Found"
    else
        print_warning "Environment file: Missing .env"
    fi

    echo ""
}

# Quick setup for new developers
setup_dev() {
    print_header "Development Environment Setup"

    print_success "Installing dependencies..."
    npm install

    print_success "Setting up Python virtual environment..."
    python -m venv venv || true
    source venv/bin/activate || true

    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi

    print_success "Building TypeScript bridge..."
    npm run build:bridge

    print_success "Running initial tests..."
    npm run test:python

    print_success "🎉 Development environment ready!"
}

# Quick testing suite
run_tests() {
    print_header "Running Test Suite"

    print_success "Running Python tests..."
    npm run test:python

    print_success "Running TypeScript tests..."
    npm run test:typescript

    print_success "Running system health check..."
    npm run health:full

    print_success "🧪 All tests completed!"
}

# Development server start
start_dev() {
    print_header "Starting Development Servers"

    print_success "Starting TypeScript bridge..."
    npm run dev:bridge &

    sleep 2

    print_success "Running health check..."
    health_check

    print_success "🔥 Development environment running!"
    echo "TypeScript Bridge: http://localhost:3001"
    echo "Press Ctrl+C to stop"

    wait
}

# Performance check
perf_check() {
    print_header "Performance Check"

    print_success "Testing production pipeline performance..."
    time python scripts/test_production_pipeline.py

    print_success "Checking system resources..."
    echo "Memory usage:"
    free -h
    echo ""
    echo "Disk usage:"
    df -h .
}

# Main script logic
case "$1" in
    "health"|"check")
        health_check
        ;;
    "setup")
        setup_dev
        ;;
    "test")
        run_tests
        ;;
    "start"|"dev")
        start_dev
        ;;
    "perf"|"performance")
        perf_check
        ;;
    "help"|"")
        print_header "Available Commands"
        echo "health    - Run system health check"
        echo "setup     - Setup development environment"
        echo "test      - Run all tests"
        echo "start     - Start development servers"
        echo "perf      - Run performance checks"
        echo "help      - Show this help"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Run './dev-utils.sh help' for available commands"
        exit 1
        ;;
esac