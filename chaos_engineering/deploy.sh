#!/bin/bash

# PAKE System - Chaos Engineering Deployment Script
# Section 3.2: Implementing Proactive Resilience

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 PAKE System - Chaos Engineering Deployment${NC}"
echo -e "=================================================="

# Check if we're in the right directory
if [ ! -f "chaos_config.yaml" ]; then
    echo -e "${RED}❌ Error: chaos_config.yaml not found. Please run this script from the chaos_engineering directory.${NC}"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${BLUE}[INFO]${NC} Checking prerequisites..."

# Check Python
if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 is required but not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✅${NC} Python 3 found"

# Check pip
if ! command_exists pip3; then
    echo -e "${RED}❌ pip3 is required but not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✅${NC} pip3 found"

# Check kubectl
if ! command_exists kubectl; then
    echo -e "${YELLOW}⚠️${NC} kubectl not found. Kubernetes operations will not be available."
else
    echo -e "${GREEN}✅${NC} kubectl found"
fi

# Install Python dependencies
echo -e "${BLUE}[INFO]${NC} Installing Python dependencies..."
pip3 install -r requirements.txt

# Install Chaos Toolkit
echo -e "${BLUE}[INFO]${NC} Installing Chaos Toolkit..."
pip3 install chaostoolkit chaostoolkit-kubernetes chaostoolkit-prometheus

# Verify installation
echo -e "${BLUE}[INFO]${NC} Verifying Chaos Toolkit installation..."
if chaos --version >/dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} Chaos Toolkit installed successfully"
else
    echo -e "${RED}❌${NC} Chaos Toolkit installation failed"
    exit 1
fi

# Create results directory
echo -e "${BLUE}[INFO]${NC} Creating results directory..."
mkdir -p results

# Set up environment variables template
echo -e "${BLUE}[INFO]${NC} Setting up environment variables..."
cat > .env.template << 'EOF'
# PAKE System - Chaos Engineering Environment Variables
# Copy this file to .env and fill in your values

# Staging Environment
export CHAOS_STAGING_URL="https://staging.pake-system.com"
export CHAOS_DATABASE_URL="postgresql://staging_user:staging_password@staging-db:5432/pake_staging"
export CHAOS_REDIS_URL="redis://staging-redis:6379/0"
export CHAOS_KUBECONFIG="/path/to/staging-kubeconfig"
export CHAOS_PROMETHEUS_URL="http://staging-prometheus:9090"

# Restore Environment (for backup/restore tests)
export CHAOS_RESTORE_URL="https://restore.pake-system.com"
export CHAOS_RESTORE_DATABASE_URL="postgresql://restore_user:restore_password@restore-db:5432/pake_restore"

# Monitoring
export CHAOS_ALERT_WEBHOOK="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
export CHAOS_SLACK_CHANNEL="#chaos-engineering"

# Backup Configuration
export CHAOS_BACKUP_ID=""
EOF

echo -e "${GREEN}✅${NC} Environment template created: .env.template"

# Create test script
echo -e "${BLUE}[INFO]${NC} Creating test script..."
cat > run_tests.sh << 'EOF'
#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo "⚠️  .env file not found. Using default values."
fi

# Run chaos engineering tests
echo "🧪 Running PAKE System Chaos Engineering Tests..."
python3 test_runner.py

echo "📊 Test results saved in results/ directory"
EOF

chmod +x run_tests.sh
echo -e "${GREEN}✅${NC} Test script created: run_tests.sh"

# Create Kubernetes deployment script
echo -e "${BLUE}[INFO]${NC} Creating Kubernetes deployment script..."
cat > deploy_k8s.sh << 'EOF'
#!/bin/bash

# Deploy chaos engineering to Kubernetes
echo "🚀 Deploying Chaos Engineering to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl >/dev/null 2>&1; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Apply chaos staging configuration
if [ -f "../k8s/chaos-staging.yaml" ]; then
    kubectl apply -f ../k8s/chaos-staging.yaml
    echo "✅ Chaos staging environment deployed"
else
    echo "⚠️  chaos-staging.yaml not found. Skipping Kubernetes deployment."
fi

# Check deployment status
kubectl get pods -n chaos-staging
EOF

chmod +x deploy_k8s.sh
echo -e "${GREEN}✅${NC} Kubernetes deployment script created: deploy_k8s.sh"

# Create monitoring setup script
echo -e "${BLUE}[INFO]${NC} Creating monitoring setup script..."
cat > setup_monitoring.sh << 'EOF'
#!/bin/bash

# Set up monitoring for chaos engineering
echo "📊 Setting up Chaos Engineering Monitoring..."

# Check if Prometheus is available
if curl -s http://localhost:9090/api/v1/query?query=up >/dev/null 2>&1; then
    echo "✅ Prometheus is running"
else
    echo "⚠️  Prometheus not accessible at localhost:9090"
fi

# Check if Grafana is available
if curl -s http://localhost:3000/api/health >/dev/null 2>&1; then
    echo "✅ Grafana is running"
else
    echo "⚠️  Grafana not accessible at localhost:3000"
fi

echo "📈 Monitoring setup complete"
echo "   - Prometheus: http://localhost:9090"
echo "   - Grafana: http://localhost:3000"
echo "   - Chaos Dashboard: http://localhost:8090 (when deployed)"
EOF

chmod +x setup_monitoring.sh
echo -e "${GREEN}✅${NC} Monitoring setup script created: setup_monitoring.sh"

# Display completion message
echo ""
echo -e "${GREEN}🎉 Chaos Engineering Deployment Complete!${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Copy .env.template to .env and configure your environment variables"
echo "2. Run './run_tests.sh' to execute chaos engineering tests"
echo "3. Run './deploy_k8s.sh' to deploy to Kubernetes (optional)"
echo "4. Run './setup_monitoring.sh' to verify monitoring setup"
echo ""
echo -e "${BLUE}Available Commands:${NC}"
echo "  ./run_tests.sh          - Run all chaos engineering tests"
echo "  ./deploy_k8s.sh         - Deploy to Kubernetes"
echo "  ./setup_monitoring.sh   - Set up monitoring"
echo "  python3 test_runner.py  - Run tests directly"
echo "  chaos run experiments/database_failover_test.json - Run specific experiment"
echo ""
echo -e "${GREEN}✅ Chaos Engineering is ready for use!${NC}"
