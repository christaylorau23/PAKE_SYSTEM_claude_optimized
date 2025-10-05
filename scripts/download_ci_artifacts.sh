#!/bin/bash
# Download CI Artifacts from GitHub Actions
#
# Usage:
#   ./scripts/download_ci_artifacts.sh [RUN_ID]
#   ./scripts/download_ci_artifacts.sh              # Downloads from latest run
#   ./scripts/download_ci_artifacts.sh 12345678     # Downloads from specific run

set -e

# Configuration
REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-christaylorau23}"
REPO_NAME="${GITHUB_REPOSITORY_NAME:-PAKE_SYSTEM_claude_optimized}"
OUTPUT_DIR="./ci-artifacts"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}📥 CI Artifact Downloader${NC}"
echo "================================"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ Error: GitHub CLI (gh) is not installed${NC}"
    echo "Install it with: brew install gh (macOS) or apt install gh (Ubuntu)"
    echo "Or visit: https://cli.github.com/"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not authenticated with GitHub${NC}"
    echo "Running: gh auth login"
    gh auth login
fi

# Get run ID
RUN_ID="$1"

if [ -z "$RUN_ID" ]; then
    echo -e "${YELLOW}📋 Fetching latest workflow run...${NC}"

    # Get latest run ID
    RUN_ID=$(gh run list \
        --repo "$REPO_OWNER/$REPO_NAME" \
        --limit 1 \
        --json databaseId \
        --jq '.[0].databaseId')

    if [ -z "$RUN_ID" ]; then
        echo -e "${RED}❌ Could not find any workflow runs${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Found latest run: ${RUN_ID}${NC}"
fi

# Get run details
echo -e "\n${YELLOW}📊 Fetching run details...${NC}"
RUN_INFO=$(gh run view "$RUN_ID" --repo "$REPO_OWNER/$REPO_NAME" --json status,conclusion,headBranch,displayTitle)

STATUS=$(echo "$RUN_INFO" | jq -r '.status')
CONCLUSION=$(echo "$RUN_INFO" | jq -r '.conclusion')
BRANCH=$(echo "$RUN_INFO" | jq -r '.headBranch')
TITLE=$(echo "$RUN_INFO" | jq -r '.displayTitle')

echo "Run ID: $RUN_ID"
echo "Status: $STATUS"
echo "Conclusion: $CONCLUSION"
echo "Branch: $BRANCH"
echo "Title: $TITLE"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# List artifacts
echo -e "\n${YELLOW}📦 Listing artifacts...${NC}"
ARTIFACTS=$(gh run view "$RUN_ID" --repo "$REPO_OWNER/$REPO_NAME" --json artifacts --jq '.artifacts[] | "\(.name)|\(.id)"')

if [ -z "$ARTIFACTS" ]; then
    echo -e "${RED}❌ No artifacts found for this run${NC}"
    exit 1
fi

echo "Found artifacts:"
echo "$ARTIFACTS" | while IFS='|' read -r name id; do
    echo "  • $name (ID: $id)"
done

# Download all diagnostic artifacts
echo -e "\n${YELLOW}⬇️  Downloading diagnostic artifacts...${NC}"

DOWNLOADED=0
echo "$ARTIFACTS" | while IFS='|' read -r name id; do
    # Download diagnostic artifacts (those containing 'diagnostic', 'test', or 'artifacts')
    if echo "$name" | grep -qiE "(diagnostic|test|artifacts|results)"; then
        echo -e "${GREEN}Downloading: $name${NC}"

        # Download artifact
        gh run download "$RUN_ID" \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --name "$name" \
            --dir "$OUTPUT_DIR/$name"

        DOWNLOADED=$((DOWNLOADED + 1))
    fi
done

if [ $DOWNLOADED -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No diagnostic artifacts found. Downloading all artifacts...${NC}"
    gh run download "$RUN_ID" \
        --repo "$REPO_OWNER/$REPO_NAME" \
        --dir "$OUTPUT_DIR"
fi

echo -e "\n${GREEN}✅ Download complete!${NC}"
echo -e "Artifacts saved to: ${GREEN}$OUTPUT_DIR${NC}"

# Check for diagnostic files
echo -e "\n${YELLOW}🔍 Checking for diagnostic files...${NC}"

FOUND_ENV=false
FOUND_REQ=false
FOUND_LOGS=false

if find "$OUTPUT_DIR" -name "environment.log" | grep -q .; then
    FOUND_ENV=true
    echo -e "${GREEN}✅ Found environment.log${NC}"
else
    echo -e "${RED}❌ environment.log not found${NC}"
fi

if find "$OUTPUT_DIR" -name "requirements.ci.log" | grep -q .; then
    FOUND_REQ=true
    echo -e "${GREEN}✅ Found requirements.ci.log${NC}"
else
    echo -e "${RED}❌ requirements.ci.log not found${NC}"
fi

if find "$OUTPUT_DIR" -name "*.log" -o -name "*.xml" | grep -q .; then
    FOUND_LOGS=true
    echo -e "${GREEN}✅ Found log/test files${NC}"
else
    echo -e "${RED}❌ No log files found${NC}"
fi

# Suggest next steps
echo -e "\n${GREEN}📋 Next Steps:${NC}"
echo "================================"

if [ "$FOUND_ENV" = true ] && [ "$FOUND_REQ" = true ]; then
    echo -e "${GREEN}1. Generate local snapshot:${NC}"
    echo "   python scripts/forensic_ci_analysis.py --generate-local"
    echo ""
    echo -e "${GREEN}2. Run forensic analysis:${NC}"

    # Find the artifact directory with diagnostic files
    ARTIFACT_DIR=$(find "$OUTPUT_DIR" -name "environment.log" -type f | head -1 | xargs dirname)

    if [ -n "$ARTIFACT_DIR" ]; then
        echo "   python scripts/forensic_ci_analysis.py --artifacts-dir \"$ARTIFACT_DIR\""
    else
        echo "   python scripts/forensic_ci_analysis.py --artifacts-dir \"$OUTPUT_DIR\""
    fi
else
    echo -e "${YELLOW}⚠️  Diagnostic files incomplete. You may need to update your CI workflow${NC}"
    echo "   to include environment snapshots. See ENHANCED_LOGGING.md"
fi

echo ""
echo -e "${GREEN}🔗 View run in browser:${NC}"
echo "   gh run view $RUN_ID --repo $REPO_OWNER/$REPO_NAME --web"
