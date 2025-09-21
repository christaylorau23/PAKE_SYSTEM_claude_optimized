#!/bin/bash

# GitHub Workflow OAuth Resolution Script
# This script helps resolve OAuth scope issues with GitHub workflow files

set -e

echo "🔧 GitHub Workflow OAuth Resolution Script"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: This script must be run from the PAKE System root directory"
    exit 1
fi

echo "📋 Current Status:"
echo "  - Repository: $(git remote get-url origin)"
echo "  - Branch: $(git branch --show-current)"
echo "  - Modified workflow files: $(git status --porcelain | grep '\.github/workflows/' | wc -l)"
echo ""

# Check if GitHub CLI is available
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI is available"
    GH_AVAILABLE=true
else
    echo "⚠️  GitHub CLI is not available"
    GH_AVAILABLE=false
fi

# Check if user is authenticated with GitHub CLI
if [ "$GH_AVAILABLE" = true ]; then
    if gh auth status &> /dev/null; then
        echo "✅ GitHub CLI is authenticated"
        GH_AUTHENTICATED=true
    else
        echo "⚠️  GitHub CLI is not authenticated"
        GH_AUTHENTICATED=false
    fi
else
    GH_AUTHENTICATED=false
fi

echo ""
echo "🎯 Solution Options:"
echo ""

# Option 1: GitHub CLI (if available and authenticated)
if [ "$GH_AVAILABLE" = true ] && [ "$GH_AUTHENTICATED" = true ]; then
    echo "1. ✅ Use GitHub CLI (Recommended - Ready to use)"
    echo "   Command: git push origin main"
    echo ""
fi

# Option 2: Manual web interface
echo "2. 📝 Manual GitHub Web Interface"
echo "   - Go to: https://github.com/christaylorau23/PAKE-System"
echo "   - Navigate to .github/workflows/"
echo "   - Copy updated content from local files"
echo "   - Commit via GitHub web interface"
echo ""

# Option 3: Personal Access Token
echo "3. 🔑 Personal Access Token"
echo "   - Create token with 'workflow' scope at:"
echo "     https://github.com/settings/tokens"
echo "   - Update remote: git remote set-url origin https://<token>@github.com/christaylorau23/PAKE-System.git"
echo "   - Push: git push origin main"
echo ""

# Option 4: GitHub CLI authentication
if [ "$GH_AVAILABLE" = true ] && [ "$GH_AUTHENTICATED" = false ]; then
    echo "4. 🔐 Authenticate GitHub CLI"
    echo "   Command: gh auth login"
    echo "   Then: git push origin main"
    echo ""
fi

echo "📁 Workflow Files Ready for Commit:"
git status --porcelain | grep '\.github/workflows/' | while read -r line; do
    echo "  - $(echo "$line" | cut -c4-)"
done

echo ""
echo "🚀 Quick Commands:"
echo ""

# Show current git status
echo "Current git status:"
git status --short | grep '\.github/workflows/'

echo ""
echo "To commit and push (choose appropriate method above):"
echo "  git add .github/workflows/"
echo "  git commit -m 'fix: Resolve GitHub workflow OAuth scope requirements'"
echo "  git push origin main"
echo ""

# Check if there are any workflow files that need attention
WORKFLOW_FILES=$(git status --porcelain | grep '\.github/workflows/' | wc -l)
if [ "$WORKFLOW_FILES" -gt 0 ]; then
    echo "⚠️  Note: $WORKFLOW_FILES workflow files are ready to be committed"
    echo "   These files have been updated with proper OAuth permissions"
    echo "   Choose one of the solution options above to push them to GitHub"
else
    echo "✅ All workflow files are already committed"
fi

echo ""
echo "📖 For detailed instructions, see: GITHUB_WORKFLOW_OAUTH_RESOLUTION.md"
