#!/bin/bash
# PAKE System - Phase 2 Demo Script
# Demonstrates the environmental parity implementation with act

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_demo() {
    echo -e "${PURPLE}[DEMO]${NC} $1"
}

# Demo function
run_demo() {
    local demo_name="$1"
    local demo_command="$2"

    log_demo "=== $demo_name ==="
    echo "Command: $demo_command"
    echo "Output:"
    echo "----------------------------------------"

    if eval "$demo_command"; then
        log_success "✓ Demo completed successfully"
    else
        log_error "✗ Demo failed"
    fi
    echo
}

# Main demo function
main() {
    log_info "PAKE System - Phase 2: Environmental Parity Demo"
    echo "=================================================="
    echo
    log_info "This demo shows how to use act for local GitHub Actions simulation"
    echo

    # Check prerequisites
    log_info "Checking prerequisites..."
    if ! command -v act &> /dev/null; then
        log_error "act is not installed. Please run: ./scripts/setup-phase2-act.sh"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi

    log_success "Prerequisites check passed"
    echo

    # Demo 1: List available jobs
    run_demo "1. List Available GitHub Actions Jobs" "act -l"

    # Demo 2: Show configuration
    run_demo "2. Show act Configuration" "cat .actrc"

    # Demo 3: Dry run of a simple job
    run_demo "3. Dry Run of Lint Job" "act -j lint-and-format --dry-run"

    # Demo 4: Show available workflows
    run_demo "4. Show Available Workflows" "find .github/workflows -name '*.yml' -o -name '*.yaml' | head -5"

    # Demo 5: Show Makefile commands
    run_demo "5. Show Available Make Commands" "make -f Makefile.act help"

    # Demo 6: Troubleshooting check
    run_demo "6. Troubleshooting Check" "make -f Makefile.act troubleshoot"

    log_success "Demo completed successfully!"
    echo
    log_info "Next steps:"
    log_info "1. Edit .secrets file with your actual secrets"
    log_info "2. Edit .vars file with your configuration"
    log_info "3. Run: make -f Makefile.act validate-act"
    log_info "4. Try: make -f Makefile.act test-lint"
    log_info "5. Read the guide: docs/PHASE_2_ENVIRONMENTAL_PARITY_GUIDE.md"
}

# Run main function
main "$@"
