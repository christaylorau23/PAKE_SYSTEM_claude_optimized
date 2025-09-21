#!/bin/bash

# PAKE System Dashboard Deployment Script
# This script deploys the dashboard to Vercel

set -e

echo "🚀 Deploying PAKE System Dashboard to Vercel..."

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Check if we're logged in to Vercel
if ! vercel whoami &> /dev/null; then
    echo "🔐 Please log in to Vercel..."
    vercel login
fi

# Set environment variables
echo "📝 Setting up environment variables..."
echo "Please provide your GitHub Personal Access Token:"
read -s GITHUB_TOKEN

# Deploy to Vercel
echo "🚀 Deploying to Vercel..."
vercel --prod

# Set environment variables in Vercel
echo "🔧 Setting environment variables in Vercel..."
vercel env add GITHUB_TOKEN production <<< "$GITHUB_TOKEN"
vercel env add GITHUB_REPO production <<< "christaylorau23/PAKE-System"

echo "✅ Dashboard deployed successfully!"
echo "🌐 Your dashboard is now live at: https://pake-system-dashboard.vercel.app"
echo ""
echo "📋 Next steps:"
echo "1. Visit your dashboard URL"
echo "2. Verify GitHub Actions data is loading"
echo "3. Check that workflows are displaying correctly"
echo ""
echo "🔧 To update environment variables:"
echo "vercel env add GITHUB_TOKEN production"
echo "vercel env add GITHUB_REPO production"
