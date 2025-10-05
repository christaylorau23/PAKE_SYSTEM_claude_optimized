#!/bin/bash
# PAKE System - CI Script for Fault Injection Testing
# This script ensures fault injection tests are run in CI pipeline

set -e

echo "🚀 Starting Fault Injection Testing CI Pipeline"

# Check if we're in CI environment
if [ -n "$CI" ]; then
    echo "✅ Running in CI environment"
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
else
    echo "⚠️  Not in CI environment - setting up local test environment"
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
fi

# Install test dependencies
echo "📦 Installing test dependencies..."
pip install -e ".[dev]"

# Run fault injection tests
echo "🧪 Running fault injection tests..."
python -m pytest tests/integration/test_fault_injection.py \
    -m "fault_injection" \
    -vv \
    --tb=short \
    --timeout=300 \
    --cov=src.services.ingestion \
    --cov-report=term-missing \
    --cov-report=xml:coverage-fault-injection.xml \
    --junitxml=test-results-fault-injection.xml

# Check test results
if [ $? -eq 0 ]; then
    echo "✅ Fault injection tests passed"
    exit 0
else
    echo "❌ Fault injection tests failed"
    exit 1
fi
