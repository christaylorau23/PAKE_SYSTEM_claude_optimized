#!/bin/bash

# PAKE System Web App Deployment Script
# This script deploys the PAKE System web application to Vercel

set -e

echo "🚀 Deploying PAKE System Web Application to Vercel..."

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

# Deploy to Vercel
echo "🚀 Deploying PAKE System Web App to Vercel..."
vercel --prod

echo "✅ PAKE System Web App deployed successfully!"
echo ""
echo "🌐 Your PAKE System is now live!"
echo "📚 Available endpoints:"
echo "  - Main page: https://your-app.vercel.app/"
echo "  - API docs: https://your-app.vercel.app/docs"
echo "  - Health check: https://your-app.vercel.app/health"
echo "  - System info: https://your-app.vercel.app/system"
echo ""
echo "🔧 Test the API:"
echo "  curl https://your-app.vercel.app/health"
echo "  curl 'https://your-app.vercel.app/api/v1/search?query=AI'"
echo ""
echo "🎉 Your PAKE System is ready for testing!"
