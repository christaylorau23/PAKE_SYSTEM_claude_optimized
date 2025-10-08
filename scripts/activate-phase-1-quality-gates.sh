#!/bin/bash
# PAKE System - Activate Phase 1 Quality Gates (Observe Mode)
# This script activates the first phase of the CI/CD Quality Gates rollout

set -e

echo "🚀 Activating PAKE System Phase 1 Quality Gates (Observe Mode)"
echo "================================================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check if we're in the right directory
if [ ! -f "sonar-project.properties" ]; then
    print_error "sonar-project.properties not found. Please run this script from the project root."
    exit 1
fi

# Check if GitHub Actions workflows exist
if [ ! -f ".github/workflows/quality-gates-phase-1.yml" ]; then
    print_error "Phase 1 workflow not found. Please ensure all workflow files are created."
    exit 1
fi

print_success "Prerequisites check completed"

# Phase 1 Activation Steps
print_status "Activating Phase 1: Observe Mode Quality Gates..."

# Step 1: Validate SonarQube configuration
print_status "Validating SonarQube configuration..."
if grep -q "sonar.projectKey=pake-system" sonar-project.properties; then
    print_success "SonarQube project configuration validated"
else
    print_error "SonarQube project configuration invalid"
    exit 1
fi

# Step 2: Check GitHub Actions workflow
print_status "Validating GitHub Actions workflow..."
if grep -q "Quality Gates - Phase 1" .github/workflows/quality-gates-phase-1.yml; then
    print_success "Phase 1 workflow validated"
else
    print_error "Phase 1 workflow validation failed"
    exit 1
fi

# Step 3: Display Phase 1 characteristics
echo ""
echo "📋 Phase 1 Characteristics:"
echo "============================"
echo "✅ **Non-blocking**: PRs can be merged regardless of quality status"
echo "✅ **Data Collection**: All quality metrics are measured and reported"
echo "✅ **Tool Validation**: Ensures all quality tools function correctly"
echo "✅ **Baseline Establishment**: Documents current quality state"
echo ""

# Step 4: Display quality checks
echo "🔍 Quality Checks (Observe Mode):"
echo "================================="
echo "• Static analysis (SonarQube) - **Report only**"
echo "• Security scans (Snyk) - **Report only**"
echo "• Test coverage analysis - **Report only**"
echo "• Code duplication check - **Report only**"
echo "• Cyclomatic complexity check - **Report only**"
echo "• Unit tests execution - **Report only**"
echo ""

# Step 5: Display thresholds
echo "📊 Quality Thresholds (Observe Mode):"
echo "====================================="
echo "• Test Coverage: Report if < 80%"
echo "• Code Duplication: Report if ≥ 5 files"
echo "• Cyclomatic Complexity: Report if ≥ 3 functions"
echo "• Unit Tests: Report failures"
echo ""

# Step 6: Check for required secrets
print_status "Checking for required GitHub secrets..."

# Check if SONAR_TOKEN is set (optional for Phase 1)
if [ -z "$SONAR_TOKEN" ]; then
    print_warning "SONAR_TOKEN not set. SonarQube integration will be limited."
    print_warning "Set SONAR_TOKEN in GitHub repository secrets for full functionality."
else
    print_success "SONAR_TOKEN is configured"
fi

# Check if SNYK_TOKEN is set (optional for Phase 1)
if [ -z "$SNYK_TOKEN" ]; then
    print_warning "SNYK_TOKEN not set. Security scanning will be limited."
    print_warning "Set SNYK_TOKEN in GitHub repository secrets for security analysis."
else
    print_success "SNYK_TOKEN is configured"
fi

# Step 7: Display next steps
echo ""
echo "🚀 Next Steps:"
echo "=============="
echo "1. **Commit and Push**: Commit the Phase 1 workflow to your repository"
echo "2. **Create PR**: Create a pull request to test the Phase 1 workflow"
echo "3. **Monitor Dashboard**: Watch the Unified Quality Dashboard for metrics"
echo "4. **Review Reports**: Check GitHub Actions for quality reports"
echo "5. **Plan Phase 2**: Prepare for Phase 2 transition in 1-2 weeks"
echo ""

# Step 8: Display monitoring information
echo "📈 Monitoring Information:"
echo "=========================="
echo "• **Unified Quality Dashboard**: http://localhost:3001"
echo "• **GitHub Actions**: Check workflow runs in your repository"
echo "• **SonarQube**: https://sonarcloud.io/project/overview?id=pake-system"
echo "• **Prometheus Metrics**: http://localhost:9090"
echo ""

# Step 9: Display Phase 2 preview
echo "🔮 Phase 2 Preview (Weeks 2-3):"
echo "================================"
echo "In Phase 2, these checks will become **blocking** for:"
echo "• New code smells and duplication"
echo "• Test coverage on new/modified code"
echo "• Unit test failures"
echo "• Major security vulnerabilities"
echo ""

# Step 10: Display Phase 3 preview
echo "🛡️ Phase 3 Preview (Week 4+):"
echo "=============================="
echo "In Phase 3, **zero tolerance** will be enforced for:"
echo "• All critical and blocker issues"
echo "• Security hotspots (manual review required)"
echo "• Stricter thresholds (85% coverage, <2% duplication)"
echo "• Enterprise-grade quality standards"
echo ""

# Final status
print_success "Phase 1 Quality Gates activation completed!"
echo ""
echo "🎯 **Current Status**: Phase 1 (Observe Mode) - Ready for deployment"
echo "📋 **Action Required**: Commit and push the workflow to activate"
echo "📊 **Monitoring**: Use the Unified Quality Dashboard to track progress"
echo "🚀 **Timeline**: Phase 2 transition planned for 1-2 weeks"
echo ""
print_success "Quality Gates implementation complete!"
