#!/bin/bash
# PAKE System - Simple Fault Injection Test Runner
# Lightweight script to validate fault injection tests

set -e

echo "🚀 Starting Simple Fault Injection Test Validation"

# Set up Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Install minimal dependencies for fault injection testing
echo "📦 Installing minimal test dependencies..."
pip install aioresponses pytest-asyncio aiohttp

# Run fault injection validation script
echo "🧪 Running fault injection validation..."
python scripts/validate_fault_injection.py

# Check results
if [ $? -eq 0 ]; then
    echo "✅ Fault injection tests passed"
    echo "🎯 System demonstrates resilience to external API failures"
    exit 0
else
    echo "❌ Some fault injection tests failed"
    echo "🔧 System needs improvement in error handling"
    exit 1
fi
