#!/bin/bash

# 🚀 PAKE System WSL Development Setup Script
# Complete first-time setup for WSL Ubuntu environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}🚀 PAKE System - $1${NC}"
    echo "----------------------------------------"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Step 1: Create .env file
setup_environment() {
    print_header "Setting up Environment Variables"

    if [ -f ".env" ]; then
        print_warning ".env file already exists. Backing up to .env.backup"
        cp .env .env.backup
    fi

    print_info "Creating development .env file..."
    cat > .env << 'EOF'
# PAKE System Development Environment Configuration

# =============================================================================
# API CONFIGURATION
# =============================================================================

# External API Keys (REQUIRED - UPDATE THESE)
FIRECRAWL_API_KEY=fc-your-development-firecrawl-api-key
PUBMED_EMAIL=your-development-email@example.com

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# PostgreSQL Database (REQUIRED)
DATABASE_URL=postgresql://pakeuser:REDACTED_SECRET@localhost:5432/pake_db

# Database Connection Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

# Redis Cache (REQUIRED)
REDIS_URL=redis://localhost:6379/0

# Cache Settings
CACHE_TTL_SECONDS=300
CACHE_MAX_CONNECTIONS=50
CACHE_TIMEOUT=5
CACHE_RETRY_ON_TIMEOUT=true

# =============================================================================
# SERVICE CONFIGURATION
# =============================================================================

# Service Ports
MCP_SERVER_PORT=8000
BRIDGE_PORT=3001

# Vault Configuration
VAULT_PATH=./vault

# =============================================================================
# DEVELOPMENT SETTINGS
# =============================================================================

# Debug Mode (ENABLED FOR DEVELOPMENT)
DEBUG=true
DEVELOPMENT_MODE=true

# Environment
ENVIRONMENT=development
ENVIRONMENT_NAME=Development

# =============================================================================
# FEATURE FLAGS
# =============================================================================

# ML Features
ENABLE_ML_ENHANCEMENT=true
ENABLE_SEMANTIC_SEARCH=true
ENABLE_CONTENT_SUMMARIZATION=true
ENABLE_KNOWLEDGE_GRAPH=true

# Analytics Features
ENABLE_RESEARCH_ANALYTICS=true
ENABLE_PATTERN_ANALYSIS=true
ENABLE_INSIGHT_GENERATION=true

# =============================================================================
# SECURITY CONFIGURATION (RELAXED FOR DEVELOPMENT)
# =============================================================================

# HTTPS Configuration (DISABLED FOR DEVELOPMENT)
FORCE_HTTPS=false

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:8000
ALLOWED_METHODS=GET,POST,OPTIONS
ALLOWED_HEADERS=Content-Type,Authorization,X-API-Key

# Rate Limiting (RELAXED FOR DEVELOPMENT)
RATE_LIMIT_PER_MINUTE=1000
RATE_LIMIT_BURST=2000
RATE_LIMIT_WINDOW=60

# Security Headers (DISABLED FOR DEVELOPMENT)
SECURITY_HEADERS=false

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log Levels
LOG_LEVEL=DEBUG
LOG_FORMAT=text
LOG_FILE_PATH=./logs/pake-system.log

# =============================================================================
# EXTERNAL SERVICES
# =============================================================================

# Firecrawl Configuration
FIRECRAWL_BASE_URL=https://api.firecrawl.dev/v0
FIRECRAWL_TIMEOUT=30
FIRECRAWL_RETRY_ATTEMPTS=3

# arXiv Configuration
ARXIV_BASE_URL=http://export.arxiv.org/api/query
ARXIV_TIMEOUT=30
ARXIV_RETRY_ATTEMPTS=3

# PubMed Configuration
PUBMED_BASE_URL=https://eutils.ncbi.nlm.nih.gov/entrez/eutils
PUBMED_TIMEOUT=30
PUBMED_RETRY_ATTEMPTS=3
EOF

    print_success "Environment file created successfully!"
    print_warning "IMPORTANT: Update FIRECRAWL_API_KEY and PUBMED_EMAIL in .env file"
}

# Step 2: Install PostgreSQL
install_postgresql() {
    print_header "Installing PostgreSQL"

    print_info "Updating package list..."
    sudo apt update

    print_info "Installing PostgreSQL..."
    sudo apt install -y postgresql postgresql-contrib

    print_info "Starting PostgreSQL service..."
    sudo service postgresql start

    print_info "Enabling PostgreSQL to start on boot..."
    sudo systemctl enable postgresql

    print_success "PostgreSQL installed and started successfully!"
}

# Step 3: Setup Database
setup_database() {
    print_header "Setting up Database"

    print_info "Creating database and user..."
    sudo -u postgres psql << 'EOF'
CREATE DATABASE pake_db;
CREATE USER pakeuser WITH PASSWORD 'REDACTED_SECRET';
GRANT ALL PRIVILEGES ON DATABASE pake_db TO pakeuser;
ALTER USER pakeuser CREATEDB;
\q
EOF

    print_success "Database and user created successfully!"
}

# Step 4: Install Redis
install_redis() {
    print_header "Installing Redis"

    print_info "Installing Redis server..."
    sudo apt install -y redis-server

    print_info "Starting Redis service..."
    sudo service redis-server start

    print_info "Enabling Redis to start on boot..."
    sudo systemctl enable redis-server

    print_success "Redis installed and started successfully!"
}

# Step 5: Setup Python Environment
setup_python_env() {
    print_header "Setting up Python Environment"

    if [ -d ".venv" ]; then
        print_warning "Virtual environment already exists"
    else
        print_info "Creating Python virtual environment..."
        python3 -m venv .venv
    fi

    print_info "Activating virtual environment..."
    source .venv/bin/activate

    print_info "Upgrading pip..."
    pip install --upgrade pip

    print_info "Installing dependencies..."
    pip install -r requirements.txt

    print_success "Python environment setup complete!"
}

# Step 6: Setup Node.js Environment
setup_node_env() {
    print_header "Setting up Node.js Environment"

    if command -v nvm &> /dev/null; then
        print_info "NVM already installed"
    else
        print_info "Installing NVM..."
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
        source ~/.bashrc
    fi

    print_info "Installing Node.js 18..."
    nvm install 18
    nvm use 18

    print_info "Installing dependencies..."
    npm install

    print_success "Node.js environment setup complete!"
}

# Step 7: Create necessary directories
create_directories() {
    print_header "Creating Required Directories"

    mkdir -p logs
    mkdir -p vault
    mkdir -p backups
    mkdir -p vault-backups

    print_success "Directories created successfully!"
}

# Step 8: Run database migrations
run_migrations() {
    print_header "Running Database Migrations"

    print_info "Activating virtual environment..."
    source .venv/bin/activate

    print_info "Running Alembic migrations..."
    alembic upgrade head

    print_success "Database migrations completed!"
}

# Main execution
main() {
    print_header "PAKE System WSL Development Setup"
    print_info "This script will set up your complete development environment"
    echo ""

    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        print_error "Please do not run this script as root"
        exit 1
    fi

    # Execute setup steps
    setup_environment
    install_postgresql
    setup_database
    install_redis
    setup_python_env
    setup_node_env
    create_directories
    run_migrations

    print_header "Setup Complete! 🎉"
    echo ""
    print_success "Your PAKE System development environment is ready!"
    echo ""
    print_info "Next steps:"
    echo "1. Update API keys in .env file (FIRECRAWL_API_KEY, PUBMED_EMAIL)"
    echo "2. Start the Bridge server: nvm use 18 && yarn run start:bridge"
    echo "3. Start the Python backend: source .venv/bin/activate && python mcp_server_multitenant.py"
    echo ""
    print_info "Health check commands:"
    echo "- Bridge: curl http://localhost:3001/health"
    echo "- Python API: curl http://localhost:8000/docs"
    echo ""
}

# Run main function
main "$@"
