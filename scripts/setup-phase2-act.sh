#!/bin/bash
# PAKE System - Phase 2: Environmental Parity Setup Script
# This script installs and configures act for local GitHub Actions simulation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Check if Docker is running
check_docker() {
    log_info "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi

    log_success "Docker is installed and running"
}

# Install act
install_act() {
    log_info "Installing act..."

    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install act
        else
            log_error "Homebrew not found. Please install Homebrew first or install act manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows
        if command -v choco &> /dev/null; then
            choco install act-cli
        elif command -v winget &> /dev/null; then
            winget install --id=nektos.act
        else
            log_error "Package manager not found. Please install act manually."
            exit 1
        fi
    else
        log_error "Unsupported OS: $OSTYPE"
        exit 1
    fi

    log_success "act installed successfully"
}

# Configure act
configure_act() {
    log_info "Configuring act..."

    # Create .actrc if it doesn't exist
    if [[ ! -f .actrc ]]; then
        log_info "Creating .actrc configuration file..."
        cat > .actrc << 'EOF'
# PAKE System - act Configuration
-P ubuntu-latest=catthehacker/ubuntu:full-22.04
-P ubuntu-20.04=catthehacker/ubuntu:full-20.04
-P ubuntu-18.04=catthehacker/ubuntu:full-18.04
--container-architecture linux/amd64
--bind
--artifact-server-path /tmp/act-artifacts
--secret-file .secrets
--var-file .vars
--verbose
EOF
        log_success "Created .actrc configuration file"
    else
        log_info ".actrc already exists, skipping creation"
    fi

    # Create .secrets file if it doesn't exist
    if [[ ! -f .secrets ]]; then
        log_warning ".secrets file not found. Please create it with your secrets."
        log_info "You can copy from .secrets.example if available"
    else
        log_success ".secrets file found"
    fi

    # Create .vars file if it doesn't exist
    if [[ ! -f .vars ]]; then
        log_warning ".vars file not found. Please create it with your variables."
        log_info "You can copy from .vars.example if available"
    else
        log_success ".vars file found"
    fi
}

# Test act installation
test_act() {
    log_info "Testing act installation..."

    # Check act version
    if act --version &> /dev/null; then
        log_success "act is working correctly"
        act --version
    else
        log_error "act installation failed"
        exit 1
    fi
}

# List available workflows
list_workflows() {
    log_info "Available GitHub Actions workflows:"
    find .github/workflows -name "*.yml" -o -name "*.yaml" | while read -r workflow; do
        echo "  - $workflow"
    done
}

# Main execution
main() {
    log_info "Starting Phase 2: Environmental Parity Setup"
    log_info "This will install and configure act for local GitHub Actions simulation"

    check_docker
    install_act
    configure_act
    test_act
    list_workflows

    log_success "Phase 2 setup completed successfully!"
    log_info "Next steps:"
    log_info "1. Edit .secrets file with your actual secrets"
    log_info "2. Edit .vars file with your configuration variables"
    log_info "3. Run 'act -l' to list available jobs"
    log_info "4. Run 'act -j <job-name>' to test specific jobs"
    log_info "5. Run 'act' to simulate the entire workflow"
}

# Run main function
main "$@"
