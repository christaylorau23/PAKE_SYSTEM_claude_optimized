#!/bin/bash
# Fix NPM audit issues

echo "🔍 Running NPM audit..."
npm audit

echo "🔧 Fixing NPM audit issues..."
npm audit fix --force

echo "✅ NPM audit fix completed"
