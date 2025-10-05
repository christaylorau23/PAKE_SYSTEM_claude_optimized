#!/bin/bash
# Integrated Local Workflow Debugger
# Combines Phase 1 (Forensic Analysis) + Phase 2 (act simulation)
#
# Usage:
#   ./scripts/debug_workflow_local.sh <job-name>              # Debug specific job
#   ./scripts/debug_workflow_local.sh lint-and-format         # Example
#   ./scripts/debug_workflow_local.sh --workflow ci.yml       # Debug entire workflow
#   ./scripts/debug_workflow_local.sh --compare <run-id>      # Compare local vs CI

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
ACT_ARTIFACTS_DIR="/tmp/act-artifacts"
LOCAL_SNAPSHOT_DIR="./local-snapshot"
ANALYSIS_OUTPUT_DIR="./debug-analysis"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   🔬 Integrated Local Workflow Debugger              ║${NC}"
echo -e "${CYAN}║   Phase 1 (Forensic) + Phase 2 (act) Integration     ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Parse arguments
JOB_NAME=""
WORKFLOW_FILE=""
COMPARE_RUN_ID=""
MODE="job"

while [[ $# -gt 0 ]]; do
    case $1 in
        --workflow)
            MODE="workflow"
            WORKFLOW_FILE="$2"
            shift 2
            ;;
        --compare)
            MODE="compare"
            COMPARE_RUN_ID="$2"
            shift 2
            ;;
        --help|-h)
            cat <<EOF
${GREEN}Integrated Local Workflow Debugger${NC}

${YELLOW}Usage:${NC}
  $0 <job-name>                    Debug specific job locally
  $0 --workflow <workflow.yml>     Debug entire workflow
  $0 --compare <run-id>            Compare local vs CI run

${YELLOW}Examples:${NC}
  $0 lint-and-format              Run lint job, capture artifacts, analyze
  $0 unit-tests                   Run unit tests locally with analysis
  $0 --workflow ci.yml            Run full CI workflow locally
  $0 --compare 12345678           Compare local run with CI run 12345678

${YELLOW}Features:${NC}
  ✓ Runs workflows locally with act (Phase 2)
  ✓ Captures artifacts automatically
  ✓ Generates environment snapshot
  ✓ Runs forensic analysis (Phase 1)
  ✓ Compares local vs CI environments
  ✓ Provides actionable recommendations

${YELLOW}Requirements:${NC}
  - Docker must be running
  - act must be installed (make -f Makefile.act setup-act)
  - .secrets and .vars files configured

EOF
            exit 0
            ;;
        *)
            JOB_NAME="$1"
            shift
            ;;
    esac
done

# Validation
echo -e "${BLUE}🔍 Step 1: Validating prerequisites...${NC}"

if ! command -v act &> /dev/null; then
    echo -e "${RED}❌ Error: act is not installed${NC}"
    echo "Run: make -f Makefile.act setup-act"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    echo "Start Docker and try again"
    exit 1
fi

if [ ! -f ".actrc" ]; then
    echo -e "${YELLOW}⚠️  Warning: .actrc not found${NC}"
    echo "Run: make -f Makefile.act setup-act"
fi

echo -e "${GREEN}✅ Prerequisites validated${NC}"

# Create output directories
mkdir -p "$ACT_ARTIFACTS_DIR"
mkdir -p "$LOCAL_SNAPSHOT_DIR"
mkdir -p "$ANALYSIS_OUTPUT_DIR"

# Step 2: Generate local environment snapshot
echo -e "\n${BLUE}📸 Step 2: Generating local environment snapshot...${NC}"
python scripts/forensic_ci_analysis.py \
    --generate-local \
    --local-snapshot-dir "$LOCAL_SNAPSHOT_DIR" \
    2>/dev/null || echo -e "${YELLOW}⚠️  Snapshot generation had warnings${NC}"

echo -e "${GREEN}✅ Local snapshot captured${NC}"

# Step 3: Run workflow locally with act
echo -e "\n${BLUE}🚀 Step 3: Running workflow locally with act...${NC}"

ACT_RUN_LOG="$ANALYSIS_OUTPUT_DIR/act_run_${TIMESTAMP}.log"

if [ "$MODE" == "workflow" ]; then
    echo -e "${CYAN}Running workflow: ${WORKFLOW_FILE}${NC}"
    act -W ".github/workflows/${WORKFLOW_FILE}" \
        --artifact-server-path "$ACT_ARTIFACTS_DIR" \
        --verbose 2>&1 | tee "$ACT_RUN_LOG"

elif [ "$MODE" == "job" ]; then
    if [ -z "$JOB_NAME" ]; then
        echo -e "${RED}❌ Error: Job name required${NC}"
        echo "Usage: $0 <job-name>"
        echo "Available jobs:"
        act -l
        exit 1
    fi

    echo -e "${CYAN}Running job: ${JOB_NAME}${NC}"
    act -j "$JOB_NAME" \
        --artifact-server-path "$ACT_ARTIFACTS_DIR" \
        --verbose 2>&1 | tee "$ACT_RUN_LOG"

elif [ "$MODE" == "compare" ]; then
    echo -e "${CYAN}Downloading CI run ${COMPARE_RUN_ID} for comparison...${NC}"
    ./scripts/download_ci_artifacts.sh "$COMPARE_RUN_ID"

    echo -e "${CYAN}Running same workflow locally...${NC}"
    # Determine which workflow to run based on CI run
    # For now, run the main CI workflow
    act -W ".github/workflows/ci.yml" \
        --artifact-server-path "$ACT_ARTIFACTS_DIR" \
        --verbose 2>&1 | tee "$ACT_RUN_LOG"
fi

ACT_EXIT_CODE=$?

if [ $ACT_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Workflow completed successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Workflow completed with exit code: ${ACT_EXIT_CODE}${NC}"
fi

# Step 4: Capture and organize artifacts
echo -e "\n${BLUE}📦 Step 4: Capturing artifacts from local run...${NC}"

LOCAL_ARTIFACTS_DIR="$ANALYSIS_OUTPUT_DIR/artifacts_${TIMESTAMP}"
mkdir -p "$LOCAL_ARTIFACTS_DIR"

# Copy artifacts from act's artifact server
if [ -d "$ACT_ARTIFACTS_DIR" ]; then
    cp -r "$ACT_ARTIFACTS_DIR"/* "$LOCAL_ARTIFACTS_DIR/" 2>/dev/null || true
    ARTIFACT_COUNT=$(find "$LOCAL_ARTIFACTS_DIR" -type f | wc -l)
    echo -e "${GREEN}✅ Captured ${ARTIFACT_COUNT} artifact files${NC}"
else
    echo -e "${YELLOW}⚠️  No artifacts directory found${NC}"
fi

# Copy environment snapshot to artifacts
cp -r "$LOCAL_SNAPSHOT_DIR"/* "$LOCAL_ARTIFACTS_DIR/" 2>/dev/null || true

# Extract diagnostic information from act log
echo -e "\n${BLUE}🔍 Step 5: Extracting diagnostic information...${NC}"

# Find errors in act log
echo -e "${CYAN}Analyzing act execution log...${NC}"
ERRORS=$(grep -i "error\|failed\|exception" "$ACT_RUN_LOG" | head -20)
if [ -n "$ERRORS" ]; then
    echo -e "${YELLOW}Found potential errors:${NC}"
    echo "$ERRORS" | head -5
fi

# Step 6: Run forensic analysis
echo -e "\n${BLUE}🔬 Step 6: Running forensic analysis...${NC}"

ANALYSIS_REPORT="$ANALYSIS_OUTPUT_DIR/analysis_report_${TIMESTAMP}.json"

# Check if we have artifacts to analyze
if [ -d "$LOCAL_ARTIFACTS_DIR" ] && [ "$(ls -A $LOCAL_ARTIFACTS_DIR)" ]; then
    python scripts/forensic_ci_analysis.py \
        --artifacts-dir "$LOCAL_ARTIFACTS_DIR" \
        --output-json "$ANALYSIS_REPORT" 2>&1 | tee "$ANALYSIS_OUTPUT_DIR/analysis_${TIMESTAMP}.log"

    ANALYSIS_EXIT_CODE=$?

    if [ $ANALYSIS_EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✅ Forensic analysis completed${NC}"
    else
        echo -e "${YELLOW}⚠️  Analysis completed with warnings${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No artifacts found to analyze${NC}"
    echo "This may be normal if the workflow didn't generate artifacts"
fi

# Step 7: Compare with CI if requested
if [ "$MODE" == "compare" ] && [ -n "$COMPARE_RUN_ID" ]; then
    echo -e "\n${BLUE}📊 Step 7: Comparing local vs CI run...${NC}"

    CI_ARTIFACTS_DIR="./ci-artifacts"
    if [ -d "$CI_ARTIFACTS_DIR" ]; then
        echo -e "${CYAN}Running comparison analysis...${NC}"

        # Find the first artifact directory in CI artifacts
        CI_ARTIFACT_SUBDIR=$(find "$CI_ARTIFACTS_DIR" -name "environment.log" -type f | head -1 | xargs dirname)

        if [ -n "$CI_ARTIFACT_SUBDIR" ]; then
            python scripts/forensic_ci_analysis.py \
                --artifacts-dir "$CI_ARTIFACT_SUBDIR" \
                --output-json "$ANALYSIS_OUTPUT_DIR/ci_analysis_${TIMESTAMP}.json"

            echo -e "${GREEN}✅ CI analysis completed${NC}"
            echo -e "${CYAN}Compare reports at:${NC}"
            echo "  Local: $ANALYSIS_REPORT"
            echo "  CI:    $ANALYSIS_OUTPUT_DIR/ci_analysis_${TIMESTAMP}.json"
        fi
    fi
fi

# Step 8: Generate summary report
echo -e "\n${BLUE}📋 Step 8: Generating debug summary...${NC}"

SUMMARY_FILE="$ANALYSIS_OUTPUT_DIR/debug_summary_${TIMESTAMP}.md"

cat > "$SUMMARY_FILE" <<EOF
# Local Workflow Debug Summary

**Timestamp**: $(date)
**Mode**: $MODE
**Job/Workflow**: ${JOB_NAME:-$WORKFLOW_FILE}
**Exit Code**: $ACT_EXIT_CODE

---

## Execution Details

- **act Log**: \`$ACT_RUN_LOG\`
- **Artifacts**: \`$LOCAL_ARTIFACTS_DIR\`
- **Analysis Report**: \`$ANALYSIS_REPORT\`

## Quick Status

- Workflow Status: $([ $ACT_EXIT_CODE -eq 0 ] && echo "✅ Success" || echo "❌ Failed (exit code $ACT_EXIT_CODE)")
- Artifacts Captured: $(find "$LOCAL_ARTIFACTS_DIR" -type f 2>/dev/null | wc -l) files
- Analysis Status: $([ -f "$ANALYSIS_REPORT" ] && echo "✅ Complete" || echo "⚠️  Not available")

## First Error (if any)

\`\`\`
$(grep -i "error\|failed" "$ACT_RUN_LOG" | head -3)
\`\`\`

## Next Steps

1. Review act execution log: \`cat $ACT_RUN_LOG\`
2. Review forensic analysis: \`cat $ANALYSIS_REPORT\`
3. Check artifacts: \`ls -la $LOCAL_ARTIFACTS_DIR\`
4. Compare with CI if needed: \`./scripts/debug_workflow_local.sh --compare <run-id>\`

---

Generated by Integrated Local Workflow Debugger
EOF

echo -e "${GREEN}✅ Debug summary generated${NC}"

# Final output
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   📊 Debug Session Complete                          ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📁 Debug artifacts saved to:${NC}"
echo "   ${ANALYSIS_OUTPUT_DIR}/"
echo ""

echo -e "${YELLOW}📄 Key files:${NC}"
echo "   • Summary:  ${SUMMARY_FILE}"
echo "   • Act Log:  ${ACT_RUN_LOG}"
if [ -f "$ANALYSIS_REPORT" ]; then
    echo "   • Analysis: ${ANALYSIS_REPORT}"
fi
echo "   • Artifacts: ${LOCAL_ARTIFACTS_DIR}/"
echo ""

if [ $ACT_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Workflow succeeded locally!${NC}"
    echo ""
    echo "If this fails in CI, run:"
    echo "  ${0} --compare <ci-run-id>"
else
    echo -e "${YELLOW}⚠️  Workflow failed locally (exit code: ${ACT_EXIT_CODE})${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Review the act log:"
    echo "     ${CYAN}less ${ACT_RUN_LOG}${NC}"
    echo ""
    if [ -f "$ANALYSIS_REPORT" ]; then
        echo "  2. Check forensic analysis recommendations:"
        echo "     ${CYAN}cat ${ANALYSIS_REPORT} | jq '.recommendations'${NC}"
        echo ""
    fi
    echo "  3. View debug summary:"
    echo "     ${CYAN}cat ${SUMMARY_FILE}${NC}"
fi

echo ""
echo -e "${BLUE}💡 Pro tips:${NC}"
echo "  • Add -vv to pytest commands in workflows for more verbose output"
echo "  • Check ${ACT_ARTIFACTS_DIR} for captured test artifacts"
echo "  • Use 'make -f Makefile.act troubleshoot' to verify setup"
echo "  • Compare local vs CI with: ${0} --compare <run-id>"
echo ""

exit $ACT_EXIT_CODE
