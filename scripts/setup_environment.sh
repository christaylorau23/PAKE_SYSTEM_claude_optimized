#!/bin/bash
# Environment Setup and Validation Script
# Ensures consistent Python 3.12.8 environment across all development setups

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Required versions
PYTHON_VERSION="3.12.8"
POETRY_VERSION="1.8.3"
NODE_VERSION="22.18.0"

echo -e "${BLUE}🚀 PAKE System Environment Setup${NC}"
echo "=================================="

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    echo -e "${BLUE}Checking Python version...${NC}"
    if command_exists python3; then
        PYTHON_CURRENT=$(python3 --version | cut -d' ' -f2)
        if [ "$PYTHON_CURRENT" = "$PYTHON_VERSION" ]; then
            print_status 0 "Python $PYTHON_CURRENT"
        else
            echo -e "${RED}❌ Python version mismatch: Expected $PYTHON_VERSION, found $PYTHON_CURRENT${NC}"
            echo -e "${YELLOW}💡 Install Python $PYTHON_VERSION using pyenv:${NC}"
            echo "   pyenv install $PYTHON_VERSION"
            echo "   pyenv local $PYTHON_VERSION"
            return 1
        fi
    else
        echo -e "${RED}❌ Python3 not found${NC}"
        return 1
    fi
}

# Check Poetry installation
check_poetry() {
    echo -e "${BLUE}Checking Poetry installation...${NC}"
    if command_exists poetry; then
        POETRY_CURRENT=$(poetry --version | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
        if [ "$POETRY_CURRENT" = "$POETRY_VERSION" ]; then
            print_status 0 "Poetry $POETRY_CURRENT"
        else
            echo -e "${YELLOW}⚠️  Poetry version mismatch: Expected $POETRY_VERSION, found $POETRY_CURRENT${NC}"
            echo -e "${YELLOW}💡 Update Poetry:${NC}"
            echo "   curl -sSL https://install.python-poetry.org | python3 -"
        fi
    else
        echo -e "${RED}❌ Poetry not found${NC}"
        echo -e "${YELLOW}💡 Install Poetry:${NC}"
        echo "   curl -sSL https://install.python-poetry.org | python3 -"
        return 1
    fi
}

# Check Node.js version
check_node() {
    echo -e "${BLUE}Checking Node.js version...${NC}"
    if command_exists node; then
        NODE_CURRENT=$(node --version | cut -d'v' -f2)
        NODE_MAJOR=$(echo $NODE_CURRENT | cut -d'.' -f1)
        NODE_REQUIRED_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)
        if [ "$NODE_MAJOR" = "$NODE_REQUIRED_MAJOR" ]; then
            print_status 0 "Node.js v$NODE_CURRENT"
        else
            echo -e "${YELLOW}⚠️  Node.js version mismatch: Expected v$NODE_VERSION, found v$NODE_CURRENT${NC}"
            echo -e "${YELLOW}💡 Update Node.js using nvm:${NC}"
            echo "   nvm install $NODE_VERSION"
            echo "   nvm use $NODE_VERSION"
        fi
    else
        echo -e "${RED}❌ Node.js not found${NC}"
        echo -e "${YELLOW}💡 Install Node.js using nvm:${NC}"
        echo "   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
        echo "   nvm install $NODE_VERSION"
        return 1
    fi
}

# Check pyenv installation
check_pyenv() {
    echo -e "${BLUE}Checking pyenv installation...${NC}"
    if command_exists pyenv; then
        print_status 0 "pyenv installed"

        # Check if correct Python version is installed
        if pyenv versions | grep -q "$PYTHON_VERSION"; then
            print_status 0 "Python $PYTHON_VERSION available in pyenv"
        else
            echo -e "${YELLOW}⚠️  Python $PYTHON_VERSION not installed in pyenv${NC}"
            echo -e "${YELLOW}💡 Install Python $PYTHON_VERSION:${NC}"
            echo "   pyenv install $PYTHON_VERSION"
        fi

        # Check local Python version
        if [ -f ".python-version" ]; then
            LOCAL_VERSION=$(cat .python-version)
            if [ "$LOCAL_VERSION" = "$PYTHON_VERSION" ]; then
                print_status 0 "Local Python version set to $LOCAL_VERSION"
            else
                echo -e "${YELLOW}⚠️  Local Python version mismatch: Expected $PYTHON_VERSION, found $LOCAL_VERSION${NC}"
                echo -e "${YELLOW}💡 Update local Python version:${NC}"
                echo "   pyenv local $PYTHON_VERSION"
            fi
        else
            echo -e "${YELLOW}⚠️  .python-version file not found${NC}"
            echo -e "${YELLOW}💡 Create .python-version file:${NC}"
            echo "   echo '$PYTHON_VERSION' > .python-version"
        fi
    else
        echo -e "${YELLOW}⚠️  pyenv not found${NC}"
        echo -e "${YELLOW}💡 Install pyenv:${NC}"
        echo "   curl https://pyenv.run | bash"
        echo "   # Add to ~/.bashrc or ~/.zshrc:"
        echo "   export PATH=\"\$HOME/.pyenv/bin:\$PATH\""
        echo "   eval \"\$(pyenv init -)\""
    fi
}

# Install dependencies
install_dependencies() {
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    if command_exists poetry; then
        poetry install --no-interaction
        print_status 0 "Python dependencies installed"
    else
        echo -e "${RED}❌ Poetry not available for dependency installation${NC}"
        return 1
    fi

    # Install Node.js dependencies if bridge directory exists
    if [ -d "src/bridge" ]; then
        echo -e "${BLUE}Installing Node.js dependencies...${NC}"
        cd src/bridge
        if command_exists npm; then
            npm ci
            print_status 0 "Node.js dependencies installed"
        else
            echo -e "${RED}❌ npm not available for dependency installation${NC}"
            return 1
        fi
        cd ../..
    fi
}

# Run environment validation
run_validation() {
    echo -e "${BLUE}Running environment validation...${NC}"
    if [ -f "scripts/validate_environment.py" ]; then
        python3 scripts/validate_environment.py
        print_status $? "Environment validation completed"
    else
        echo -e "${YELLOW}⚠️  Environment validation script not found${NC}"
    fi
}

# Main execution
main() {
    echo "Checking system requirements..."
    echo "==============================="

    # Run checks
    check_python
    check_poetry
    check_node
    check_pyenv

    echo ""
    echo "Installing dependencies..."
    echo "========================="
    install_dependencies

    echo ""
    echo "Running validation..."
    echo "===================="
    run_validation

    echo ""
    echo -e "${GREEN}🎉 Environment setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Run tests: poetry run pytest"
    echo "2. Start development server: poetry run python mcp_server_standalone.py"
    echo "3. Start TypeScript bridge: cd src/bridge && npm start"
}

# Run main function
main "$@"
