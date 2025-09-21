# PAKE+ Complete Automation Guide
## Fully Automated Workflow - Step-by-Step Implementation

### Table of Contents
1. [Prerequisites & Environment Setup](#1-prerequisites--environment-setup)
2. [Automated System Deployment](#2-automated-system-deployment)
3. [Service Orchestration & Health Monitoring](#3-service-orchestration--health-monitoring)
4. [Automated Content Ingestion Workflows](#4-automated-content-ingestion-workflows)
5. [Quality Assurance & Validation Automation](#5-quality-assurance--validation-automation)
6. [Monitoring & Alerting Automation](#6-monitoring--alerting-automation)
7. [Backup & Recovery Automation](#7-backup--recovery-automation)
8. [Maintenance & Optimization Automation](#8-maintenance--optimization-automation)
9. [Integration Testing Automation](#9-integration-testing-automation)
10. [Troubleshooting & Self-Healing](#10-troubleshooting--self-healing)

---

## 1. Prerequisites & Environment Setup

### 1.1 Automated Environment Validation Script

```bash
#!/bin/bash
# File: scripts/validate_environment.sh

set -euo pipefail

echo "🔍 PAKE+ Environment Validation Starting..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VALIDATION_FAILED=0

# Function to check command existence
check_command() {
    local cmd=$1
    local required_version=${2:-""}
    
    if command -v "$cmd" &> /dev/null; then
        local version=$(eval "$cmd --version 2>/dev/null | head -n1" || echo "Version check failed")
        echo -e "${GREEN}✅ $cmd found: $version${NC}"
        
        if [[ -n "$required_version" ]]; then
            # Add version checking logic here
            echo "   ℹ️  Required version: $required_version"
        fi
    else
        echo -e "${RED}❌ $cmd not found${NC}"
        VALIDATION_FAILED=1
    fi
}

# Function to check port availability
check_port() {
    local port=$1
    local service=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $port is in use (needed for $service)${NC}"
        echo "   Process using port: $(lsof -Pi :$port -sTCP:LISTEN | tail -n1)"
    else
        echo -e "${GREEN}✅ Port $port available for $service${NC}"
    fi
}

# Function to check system resources
check_resources() {
    echo "🖥️  System Resources Check"
    echo "------------------------"
    
    # Memory check (minimum 4GB recommended)
    local mem_gb=$(free -g | awk 'NR==2{printf "%.0f", $2}')
    if [[ $mem_gb -ge 4 ]]; then
        echo -e "${GREEN}✅ Memory: ${mem_gb}GB (sufficient)${NC}"
    else
        echo -e "${YELLOW}⚠️  Memory: ${mem_gb}GB (4GB+ recommended)${NC}"
    fi
    
    # Disk space check (minimum 10GB recommended)
    local disk_gb=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')
    if [[ $disk_gb -ge 10 ]]; then
        echo -e "${GREEN}✅ Disk space: ${disk_gb}GB available${NC}"
    else
        echo -e "${YELLOW}⚠️  Disk space: ${disk_gb}GB (10GB+ recommended)${NC}"
    fi
}

# Main validation
echo "🔧 Checking Required Software..."
echo "--------------------------------"

check_command "docker" "20.10+"
check_command "docker-compose" "1.29+"
check_command "python3" "3.11+"
check_command "node" "16+"
check_command "npm" "8+"
check_command "git" "2.30+"
check_command "curl"
check_command "jq"

echo ""
echo "🌐 Checking Required Ports..."
echo "----------------------------"

check_port 5432 "PostgreSQL"
check_port 5433 "PostgreSQL (PAKE)"
check_port 6379 "Redis"
check_port 6380 "Redis (PAKE)"
check_port 8000 "MCP Server"
check_port 3000 "API Bridge"
check_port 5678 "n8n"
check_port 8001 "Ingestion Manager"

echo ""
check_resources

echo ""
echo "🔐 Checking Docker Permissions..."
echo "--------------------------------"

if docker ps >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker daemon accessible${NC}"
else
    echo -e "${RED}❌ Cannot access Docker daemon${NC}"
    echo "   Try: sudo usermod -aG docker \$USER && newgrp docker"
    VALIDATION_FAILED=1
fi

echo ""
echo "📁 Checking Directory Structure..."
echo "---------------------------------"

required_dirs=(
    "vault"
    "mcp-servers"
    "docker"
    "scripts"
    "configs"
    "data"
    "logs"
)

for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        echo -e "${GREEN}✅ Directory exists: $dir${NC}"
    else
        echo -e "${YELLOW}⚠️  Creating directory: $dir${NC}"
        mkdir -p "$dir"
    fi
done

echo ""
echo "================================================"
if [[ $VALIDATION_FAILED -eq 0 ]]; then
    echo -e "${GREEN}🎉 Environment validation PASSED!${NC}"
    echo "Ready to proceed with PAKE+ deployment."
    exit 0
else
    echo -e "${RED}❌ Environment validation FAILED!${NC}"
    echo "Please resolve the issues above before proceeding."
    exit 1
fi
```

### 1.2 Automated Dependency Installation

```bash
#!/bin/bash
# File: scripts/install_dependencies.sh

set -euo pipefail

echo "📦 PAKE+ Dependency Installation"
echo "================================"

# Function to install Python dependencies
install_python_deps() {
    echo "🐍 Installing Python dependencies..."
    
    # Upgrade pip
    python3 -m pip install --upgrade pip
    
    # Install MCP server dependencies
    if [[ -f "mcp-servers/requirements.txt" ]]; then
        echo "   Installing MCP server dependencies..."
        python3 -m pip install -r mcp-servers/requirements.txt
    fi
    
    # Install ingestion pipeline dependencies
    if [[ -f "scripts/requirements_ingestion.txt" ]]; then
        echo "   Installing ingestion pipeline dependencies..."
        python3 -m pip install -r scripts/requirements_ingestion.txt
    fi
    
    # Install deployment script dependencies
    python3 -m pip install psycopg2-binary sqlite3
    
    echo "✅ Python dependencies installed"
}

# Function to install Node.js dependencies
install_node_deps() {
    echo "📦 Installing Node.js dependencies..."
    
    cd scripts
    
    # Install dependencies
    npm install
    
    # Install global dependencies if needed
    npm install -g pm2 nodemon
    
    cd ..
    
    echo "✅ Node.js dependencies installed"
}

# Function to install system dependencies (Ubuntu/Debian)
install_system_deps() {
    if command -v apt-get &> /dev/null; then
        echo "🔧 Installing system dependencies (apt)..."
        
        sudo apt-get update
        sudo apt-get install -y \
            curl \
            jq \
            netcat \
            lsof \
            htop \
            postgresql-client \
            redis-tools
            
        echo "✅ System dependencies installed"
    elif command -v yum &> /dev/null; then
        echo "🔧 Installing system dependencies (yum)..."
        
        sudo yum update -y
        sudo yum install -y \
            curl \
            jq \
            nc \
            lsof \
            htop \
            postgresql \
            redis
            
        echo "✅ System dependencies installed"
    else
        echo "⚠️  Package manager not detected. Please install dependencies manually:"
        echo "   - curl, jq, netcat, lsof, htop"
        echo "   - postgresql-client, redis-tools"
    fi
}

# Function to download and install NLP models
install_nlp_models() {
    echo "🧠 Installing NLP models..."
    
    # Install spaCy English model
    python3 -m spacy download en_core_web_sm
    
    # Download sentence transformer model (will be cached)
    python3 -c "
from sentence_transformers import SentenceTransformer
print('Downloading sentence transformer model...')
SentenceTransformer('all-MiniLM-L6-v2')
print('✅ Model downloaded and cached')
"
    
    echo "✅ NLP models installed"
}

# Main execution
echo "Starting dependency installation..."

install_system_deps
install_python_deps
install_node_deps
install_nlp_models

echo ""
echo "🎉 All dependencies installed successfully!"
echo "Next step: Run 'scripts/deploy_pake.py' for full deployment"
```

---

## 2. Automated System Deployment

### 2.1 Master Deployment Automation Script

```bash
#!/bin/bash
# File: scripts/master_deploy.sh

set -euo pipefail

# Configuration
DEPLOYMENT_LOG="logs/deployment_$(date +%Y%m%d_%H%M%S).log"
HEALTH_CHECK_TIMEOUT=300
HEALTH_CHECK_INTERVAL=10

# Ensure logs directory exists
mkdir -p logs

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$DEPLOYMENT_LOG"
}

# Function to run with timeout and logging
run_with_timeout() {
    local timeout=$1
    local cmd="${@:2}"
    
    log "Executing: $cmd"
    
    if timeout "$timeout" bash -c "$cmd" 2>&1 | tee -a "$DEPLOYMENT_LOG"; then
        log "✅ Command succeeded: $cmd"
        return 0
    else
        log "❌ Command failed: $cmd"
        return 1
    fi
}

# Function to wait for service health
wait_for_service() {
    local service_name=$1
    local health_url=$2
    local timeout=${3:-$HEALTH_CHECK_TIMEOUT}
    
    log "Waiting for $service_name to be healthy..."
    
    local elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if curl -f -s "$health_url" >/dev/null 2>&1; then
            log "✅ $service_name is healthy"
            return 0
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
        elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
        log "   Waiting for $service_name... (${elapsed}s/${timeout}s)"
    done
    
    log "❌ $service_name failed to become healthy within ${timeout}s"
    return 1
}

# Function to check Docker service health
check_docker_service() {
    local service_name=$1
    
    local status=$(docker-compose ps -q "$service_name" 2>/dev/null | xargs docker inspect -f '{{.State.Health.Status}}' 2>/dev/null || echo "unhealthy")
    
    if [[ "$status" == "healthy" ]] || [[ "$status" == "" ]]; then
        # If no health check defined, check if container is running
        if docker-compose ps "$service_name" | grep -q "Up"; then
            log "✅ Docker service $service_name is running"
            return 0
        fi
    fi
    
    log "❌ Docker service $service_name is not healthy (status: $status)"
    return 1
}

# Main deployment function
main_deployment() {
    log "🚀 Starting PAKE+ Master Deployment"
    log "=================================="
    
    # Step 1: Environment validation
    log "Step 1: Environment Validation"
    if ! run_with_timeout 60 "scripts/validate_environment.sh"; then
        log "❌ Environment validation failed"
        exit 1
    fi
    
    # Step 2: Dependency installation
    log "Step 2: Dependency Installation"
    if ! run_with_timeout 600 "scripts/install_dependencies.sh"; then
        log "❌ Dependency installation failed"
        exit 1
    fi
    
    # Step 3: Docker infrastructure deployment
    log "Step 3: Docker Infrastructure Deployment"
    cd docker
    
    # Pull latest images
    run_with_timeout 600 "docker-compose pull"
    
    # Start services
    run_with_timeout 120 "docker-compose up -d"
    
    cd ..
    
    # Step 4: Wait for core services
    log "Step 4: Service Health Checks"
    
    # Wait for PostgreSQL
    wait_for_service "PostgreSQL" "http://localhost:5433" 120
    
    # Wait for Redis
    if ! timeout 60 bash -c 'until redis-cli -h localhost -p 6380 ping; do sleep 2; done'; then
        log "❌ Redis failed to start"
        exit 1
    fi
    log "✅ Redis is healthy"
    
    # Step 5: Database initialization
    log "Step 5: Database Initialization"
    run_with_timeout 60 "python3 scripts/init_database.py"
    
    # Step 6: Start MCP server
    log "Step 6: MCP Server Startup"
    cd mcp-servers
    nohup python3 base_server.py > ../logs/mcp_server.log 2>&1 &
    echo $! > ../logs/mcp_server.pid
    cd ..
    
    wait_for_service "MCP Server" "http://localhost:8000/health" 120
    
    # Step 7: Start API Bridge
    log "Step 7: API Bridge Startup"
    cd scripts
    nohup node obsidian_bridge.js > ../logs/api_bridge.log 2>&1 &
    echo $! > ../logs/api_bridge.pid
    cd ..
    
    wait_for_service "API Bridge" "http://localhost:3000/health" 60
    
    # Step 8: Start Ingestion Manager
    log "Step 8: Ingestion Manager Startup"
    cd scripts
    nohup python3 ingestion_manager.py > ../logs/ingestion_manager.log 2>&1 &
    echo $! > ../logs/ingestion_manager.pid
    cd ..
    
    wait_for_service "Ingestion Manager" "http://localhost:8001" 60
    
    # Step 9: Install Git hooks
    log "Step 9: Git Hooks Installation"
    run_with_timeout 30 "python3 scripts/install-hooks-simple.py"
    
    # Step 10: Initialize sample content
    log "Step 10: Sample Content Creation"
    run_with_timeout 30 "python3 scripts/create_sample_content.py"
    
    # Step 11: Run comprehensive tests
    log "Step 11: System Integration Tests"
    run_with_timeout 300 "scripts/run_integration_tests.sh"
    
    # Step 12: Start monitoring
    log "Step 12: Monitoring Setup"
    run_with_timeout 60 "scripts/start_monitoring.sh"
    
    log "🎉 PAKE+ deployment completed successfully!"
    log "Services running:"
    log "  - PostgreSQL: localhost:5433"
    log "  - Redis: localhost:6380"
    log "  - MCP Server: http://localhost:8000"
    log "  - API Bridge: http://localhost:3000"
    log "  - n8n: http://localhost:5678"
    log "  - Ingestion Manager: http://localhost:8001"
    
    # Generate deployment report
    python3 scripts/generate_deployment_report.py
}

# Cleanup function for graceful shutdown
cleanup() {
    log "🛑 Deployment interrupted. Cleaning up..."
    
    # Kill background processes
    for pidfile in logs/*.pid; do
        if [[ -f "$pidfile" ]]; then
            local pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                log "Stopping process $pid"
                kill "$pid"
            fi
            rm -f "$pidfile"
        fi
    done
    
    exit 1
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Run main deployment
main_deployment
```

### 2.2 Database Initialization Automation

```python
#!/usr/bin/env python3
# File: scripts/init_database.py

import asyncio
import asyncpg
import logging
import os
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'port': 5433,
            'database': 'pake_knowledge',
            'user': 'pake_admin',
            'REDACTED_SECRET': 'process.env.PAKE_HARDCODED_PASSWORD || 'SECURE_HARDCODED_PASSWORD_REQUIRED''
        }
        
    async def wait_for_database(self, max_attempts=30):
        """Wait for database to be available"""
        for attempt in range(max_attempts):
            try:
                conn = await asyncpg.connect(**self.db_config)
                await conn.close()
                logger.info("✅ Database connection successful")
                return True
            except Exception as e:
                logger.info(f"Attempt {attempt + 1}/{max_attempts}: Waiting for database...")
                if attempt == max_attempts - 1:
                    logger.error(f"❌ Database connection failed: {e}")
                    return False
                await asyncio.sleep(2)
        
        return False
    
    async def run_sql_file(self, filepath):
        """Execute SQL file"""
        logger.info(f"Executing SQL file: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                sql_content = f.read()
            
            conn = await asyncpg.connect(**self.db_config)
            await conn.execute(sql_content)
            await conn.close()
            
            logger.info(f"✅ Successfully executed {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to execute {filepath}: {e}")
            return False
    
    async def verify_schema(self):
        """Verify database schema is properly initialized"""
        logger.info("Verifying database schema...")
        
        required_tables = [
            'knowledge_nodes',
            'node_connections', 
            'processing_logs',
            'confidence_history'
        ]
        
        try:
            conn = await asyncpg.connect(**self.db_config)
            
            for table in required_tables:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = $1",
                    table
                )
                
                if result > 0:
                    logger.info(f"✅ Table exists: {table}")
                else:
                    logger.error(f"❌ Missing table: {table}")
                    return False
            
            # Check for pgvector extension
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'"
            )
            
            if result > 0:
                logger.info("✅ pgvector extension installed")
            else:
                logger.error("❌ pgvector extension not found")
                return False
            
            await conn.close()
            logger.info("✅ Database schema verification passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Schema verification failed: {e}")
            return False
    
    async def create_sample_data(self):
        """Create sample data for testing"""
        logger.info("Creating sample data...")
        
        sample_nodes = [
            {
                'content': 'PAKE+ System initialization successful. All components operational.',
                'confidence_score': 1.0,
                'type': 'system',
                'verification_status': 'verified',
                'source_uri': 'local://system'
            },
            {
                'content': 'Test knowledge node for validation of ingestion pipeline functionality.',
                'confidence_score': 0.8,
                'type': 'process.env.PAKE_WEAK_PASSWORD || 'SECURE_WEAK_PASSWORD_REQUIRED'',
                'verification_status': 'verified',
                'source_uri': 'local://test'
            }
        ]
        
        try:
            conn = await asyncpg.connect(**self.db_config)
            
            for node in sample_nodes:
                await conn.execute("""
                    INSERT INTO knowledge_nodes 
                    (content, confidence_score, type, verification_status, source_uri, tags)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, 
                    node['content'],
                    node['confidence_score'], 
                    node['type'],
                    node['verification_status'],
                    node['source_uri'],
                    ['system', 'initialization']
                )
            
            await conn.close()
            logger.info("✅ Sample data created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create sample data: {e}")
            return False
    
    async def initialize(self):
        """Main initialization process"""
        logger.info("🗄️  Starting database initialization...")
        
        # Wait for database to be available
        if not await self.wait_for_database():
            return False
        
        # Database should already be initialized by Docker init.sql
        # Verify schema
        if not await self.verify_schema():
            logger.error("❌ Database schema verification failed")
            return False
        
        # Create sample data
        if not await self.create_sample_data():
            logger.error("❌ Sample data creation failed")
            return False
        
        logger.info("✅ Database initialization completed successfully")
        return True

async def main():
    initializer = DatabaseInitializer()
    success = await initializer.initialize()
    exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 3. Service Orchestration & Health Monitoring

### 3.1 Automated Service Manager

```python
#!/usr/bin/env python3
# File: scripts/service_manager.py

import asyncio
import aiohttp
import subprocess
import json
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    name: str
    health_url: str
    start_command: Optional[str] = None
    stop_command: Optional[str] = None
    restart_command: Optional[str] = None
    dependencies: List[str] = None
    max_restart_attempts: int = 3
    health_check_interval: int = 30
    startup_timeout: int = 120

class ServiceManager:
    def __init__(self):
        self.services = {
            'postgres': ServiceConfig(
                name='PostgreSQL',
                health_url='tcp://localhost:5433',
                start_command='cd docker && docker-compose start postgres',
                stop_command='cd docker && docker-compose stop postgres',
                restart_command='cd docker && docker-compose restart postgres'
            ),
            'redis': ServiceConfig(
                name='Redis',
                health_url='tcp://localhost:6380',
                start_command='cd docker && docker-compose start redis',
                stop_command='cd docker && docker-compose stop redis',
                restart_command='cd docker && docker-compose restart redis'
            ),
            'mcp_server': ServiceConfig(
                name='MCP Server',
                health_url='http://localhost:8000/health',
                start_command='cd mcp-servers && nohup python3 base_server.py > ../logs/mcp_server.log 2>&1 & echo $! > ../logs/mcp_server.pid',
                stop_command='scripts/stop_service.sh mcp_server',
                dependencies=['postgres', 'redis']
            ),
            'api_bridge': ServiceConfig(
                name='API Bridge',
                health_url='http://localhost:3000/health',
                start_command='cd scripts && nohup node obsidian_bridge.js > ../logs/api_bridge.log 2>&1 & echo $! > ../logs/api_bridge.pid',
                stop_command='scripts/stop_service.sh api_bridge',
                dependencies=['mcp_server']
            ),
            'ingestion_manager': ServiceConfig(
                name='Ingestion Manager', 
                health_url='http://localhost:8001',
                start_command='cd scripts && nohup python3 ingestion_manager.py > ../logs/ingestion_manager.log 2>&1 & echo $! > ../logs/ingestion_manager.pid',
                stop_command='scripts/stop_service.sh ingestion_manager',
                dependencies=['mcp_server']
            ),
            'n8n': ServiceConfig(
                name='n8n',
                health_url='http://localhost:5678',
                start_command='cd docker && docker-compose start n8n',
                stop_command='cd docker && docker-compose stop n8n',
                restart_command='cd docker && docker-compose restart n8n',
                dependencies=['postgres']
            )
        }
        
        self.service_status = {}
        self.restart_counts = {}
        
    async def check_tcp_health(self, host: str, port: int) -> bool:
        """Check TCP port health"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5
            )
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False
    
    async def check_http_health(self, url: str) -> bool:
        """Check HTTP endpoint health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status < 400
        except:
            return False
    
    async def check_service_health(self, service_name: str) -> bool:
        """Check health of a specific service"""
        config = self.services[service_name]
        
        if config.health_url.startswith('tcp://'):
            url_parts = config.health_url.replace('tcp://', '').split(':')
            host, port = url_parts[0], int(url_parts[1])
            return await self.check_tcp_health(host, port)
        elif config.health_url.startswith('http'):
            return await self.check_http_health(config.health_url)
        
        return False
    
    async def start_service(self, service_name: str) -> bool:
        """Start a service"""
        config = self.services[service_name]
        
        if not config.start_command:
            logger.warning(f"No start command defined for {service_name}")
            return False
        
        logger.info(f"Starting {config.name}...")
        
        try:
            # Check dependencies first
            if config.dependencies:
                for dep in config.dependencies:
                    if not await self.check_service_health(dep):
                        logger.error(f"Dependency {dep} is not healthy, cannot start {service_name}")
                        return False
            
            # Execute start command
            process = await asyncio.create_subprocess_shell(
                config.start_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"✅ {config.name} start command executed")
                
                # Wait for service to become healthy
                for attempt in range(config.startup_timeout // 5):
                    if await self.check_service_health(service_name):
                        logger.info(f"✅ {config.name} is healthy")
                        self.service_status[service_name] = 'running'
                        return True
                    await asyncio.sleep(5)
                
                logger.error(f"❌ {config.name} failed to become healthy within timeout")
                return False
            else:
                logger.error(f"❌ {config.name} start command failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting {service_name}: {e}")
            return False
    
    async def stop_service(self, service_name: str) -> bool:
        """Stop a service"""
        config = self.services[service_name]
        
        if not config.stop_command:
            logger.warning(f"No stop command defined for {service_name}")
            return False
        
        logger.info(f"Stopping {config.name}...")
        
        try:
            process = await asyncio.create_subprocess_shell(
                config.stop_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"✅ {config.name} stopped")
                self.service_status[service_name] = 'stopped'
                return True
            else:
                logger.error(f"❌ {config.name} stop command failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error stopping {service_name}: {e}")
            return False
    
    async def restart_service(self, service_name: str) -> bool:
        """Restart a service"""
        config = self.services[service_name]
        
        # Use restart command if available, otherwise stop and start
        if config.restart_command:
            logger.info(f"Restarting {config.name}...")
            
            try:
                process = await asyncio.create_subprocess_shell(
                    config.restart_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    # Wait for service to become healthy
                    for attempt in range(config.startup_timeout // 5):
                        if await self.check_service_health(service_name):
                            logger.info(f"✅ {config.name} restarted successfully")
                            return True
                        await asyncio.sleep(5)
                    
                    logger.error(f"❌ {config.name} failed to become healthy after restart")
                    return False
                else:
                    logger.error(f"❌ {config.name} restart command failed: {stderr.decode()}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Error restarting {service_name}: {e}")
                return False
        else:
            # Stop and start
            await self.stop_service(service_name)
            await asyncio.sleep(5)
            return await self.start_service(service_name)
    
    async def monitor_services(self):
        """Continuous service monitoring"""
        logger.info("🔍 Starting service monitoring...")
        
        while True:
            try:
                for service_name, config in self.services.items():
                    is_healthy = await self.check_service_health(service_name)
                    previous_status = self.service_status.get(service_name, 'unknown')
                    
                    if is_healthy:
                        if previous_status != 'running':
                            logger.info(f"✅ {config.name} is now healthy")
                        self.service_status[service_name] = 'running'
                        # Reset restart count on successful health check
                        self.restart_counts[service_name] = 0
                    else:
                        if previous_status == 'running':
                            logger.warning(f"⚠️  {config.name} health check failed")
                        
                        self.service_status[service_name] = 'unhealthy'
                        
                        # Auto-restart if within retry limit
                        restart_count = self.restart_counts.get(service_name, 0)
                        if restart_count < config.max_restart_attempts:
                            logger.info(f"🔄 Attempting auto-restart of {config.name} (attempt {restart_count + 1}/{config.max_restart_attempts})")
                            
                            if await self.restart_service(service_name):
                                logger.info(f"✅ {config.name} auto-restart successful")
                            else:
                                self.restart_counts[service_name] = restart_count + 1
                                logger.error(f"❌ {config.name} auto-restart failed")
                        else:
                            logger.error(f"❌ {config.name} exceeded max restart attempts")
                
                # Log overall system status
                healthy_services = sum(1 for status in self.service_status.values() if status == 'running')
                total_services = len(self.services)
                
                if healthy_services == total_services:
                    logger.info(f"🟢 System healthy: {healthy_services}/{total_services} services running")
                else:
                    logger.warning(f"🟡 System degraded: {healthy_services}/{total_services} services running")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in service monitoring: {e}")
                await asyncio.sleep(30)
    
    async def start_all_services(self):
        """Start all services in dependency order"""
        logger.info("🚀 Starting all services...")
        
        # Determine start order based on dependencies
        start_order = self._get_start_order()
        
        for service_name in start_order:
            if not await self.start_service(service_name):
                logger.error(f"❌ Failed to start {service_name}, aborting startup")
                return False
            
            # Small delay between services
            await asyncio.sleep(2)
        
        logger.info("✅ All services started successfully")
        return True
    
    def _get_start_order(self) -> List[str]:
        """Determine service start order based on dependencies"""
        start_order = []
        remaining = set(self.services.keys())
        
        while remaining:
            # Find services with no unmet dependencies
            ready = []
            for service_name in remaining:
                config = self.services[service_name]
                if not config.dependencies or all(dep in start_order for dep in config.dependencies):
                    ready.append(service_name)
            
            if not ready:
                # Circular dependency or invalid configuration
                logger.error("Circular dependency detected in service configuration")
                return list(remaining)
            
            # Add ready services to start order
            for service_name in ready:
                start_order.append(service_name)
                remaining.remove(service_name)
        
        return start_order
    
    async def get_system_status(self) -> Dict:
        """Get current system status"""
        status_report = {
            'timestamp': time.time(),
            'services': {},
            'overall_health': 'healthy'
        }
        
        unhealthy_count = 0
        
        for service_name, config in self.services.items():
            is_healthy = await self.check_service_health(service_name)
            restart_count = self.restart_counts.get(service_name, 0)
            
            status_report['services'][service_name] = {
                'name': config.name,
                'healthy': is_healthy,
                'status': 'running' if is_healthy else 'unhealthy',
                'restart_count': restart_count,
                'health_url': config.health_url
            }
            
            if not is_healthy:
                unhealthy_count += 1
        
        if unhealthy_count == 0:
            status_report['overall_health'] = 'healthy'
        elif unhealthy_count < len(self.services) // 2:
            status_report['overall_health'] = 'degraded'
        else:
            status_report['overall_health'] = 'critical'
        
        return status_report

# CLI interface
async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='PAKE+ Service Manager')
    parser.add_argument('command', choices=['start', 'stop', 'restart', 'status', 'monitor'])
    parser.add_argument('--service', help='Specific service to operate on')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    args = parser.parse_args()
    
    manager = ServiceManager()
    
    if args.command == 'start':
        if args.service:
            success = await manager.start_service(args.service)
            exit(0 if success else 1)
        else:
            success = await manager.start_all_services()
            exit(0 if success else 1)
    
    elif args.command == 'stop':
        if args.service:
            success = await manager.stop_service(args.service)
            exit(0 if success else 1)
        else:
            # Stop all services in reverse order
            start_order = manager._get_start_order()
            for service_name in reversed(start_order):
                await manager.stop_service(service_name)
    
    elif args.command == 'restart':
        if args.service:
            success = await manager.restart_service(args.service)
            exit(0 if success else 1)
        else:
            success = await manager.start_all_services()
            exit(0 if success else 1)
    
    elif args.command == 'status':
        status = await manager.get_system_status()
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print(f"System Health: {status['overall_health'].upper()}")
            print("Services:")
            for service_name, service_status in status['services'].items():
                health_icon = "✅" if service_status['healthy'] else "❌"
                print(f"  {health_icon} {service_status['name']}: {service_status['status']}")
                if service_status['restart_count'] > 0:
                    print(f"     Restarts: {service_status['restart_count']}")
    
    elif args.command == 'monitor':
        await manager.monitor_services()

if __name__ == "__main__":
    asyncio.run(main())
```

### 3.2 Service Stop Script

```bash
#!/bin/bash
# File: scripts/stop_service.sh

set -euo pipefail

SERVICE_NAME=$1
PID_FILE="logs/${SERVICE_NAME}.pid"

if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping $SERVICE_NAME (PID: $PID)..."
        kill "$PID"
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                echo "✅ $SERVICE_NAME stopped gracefully"
                rm -f "$PID_FILE"
                exit 0
            fi
            sleep 1
        done
        
        # Force kill if still running
        echo "Force killing $SERVICE_NAME..."
        kill -9 "$PID" 2>/dev/null || true
        rm -f "$PID_FILE"
        echo "✅ $SERVICE_NAME force stopped"
    else
        echo "⚠️ $SERVICE_NAME PID file exists but process not running"
        rm -f "$PID_FILE"
    fi
else
    echo "⚠️ No PID file found for $SERVICE_NAME"
fi
```

---

## 4. Automated Content Ingestion Workflows

### 4.1 Automated Ingestion Orchestrator

```python
#!/usr/bin/env python3
# File: scripts/ingestion_orchestrator.py

import asyncio
import aiohttp
import json
import logging
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pathlib import Path

from ingestion_pipeline import UniversalIngestionPipeline
from ingestion_manager import PAKEIngestionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IngestionOrchestrator:
    def __init__(self):
        self.pipeline = None
        self.manager = None
        self.schedule_config = {}
        self.running = False
        
    async def initialize(self):
        """Initialize ingestion components"""
        logger.info("🔄 Initializing ingestion orchestrator...")
        
        self.pipeline = UniversalIngestionPipeline()
        await self.pipeline.initialize()
        
        # Load schedule configuration
        await self.load_schedule_config()
        
        logger.info("✅ Ingestion orchestrator initialized")
    
    async def load_schedule_config(self):
        """Load ingestion schedule configuration"""
        config_path = Path("configs/ingestion_schedule.json")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                self.schedule_config = json.load(f)
        else:
            # Create default schedule
            self.schedule_config = {
                "schedules": [
                    {
                        "name": "High Priority RSS",
                        "sources": ["ArXiv AI Research", "OpenAI Blog", "Anthropic News"],
                        "frequency": "every_hour",
                        "enabled": True
                    },
                    {
                        "name": "News Feeds",
                        "sources": ["Hacker News - AI", "MIT Technology Review AI"],
                        "frequency": "every_2_hours", 
                        "enabled": True
                    },
                    {
                        "name": "Community Sources",
                        "sources": ["Reddit r/MachineLearning", "Medium AI Publications"],
                        "frequency": "every_4_hours",
                        "enabled": True
                    },
                    {
                        "name": "Email Processing",
                        "sources": ["Gmail Important"],
                        "frequency": "every_30_minutes",
                        "enabled": False  # Disabled by default
                    },
                    {
                        "name": "File System Scan",
                        "sources": ["Personal Documents"],
                        "frequency": "daily_at_02:00",
                        "enabled": False  # Disabled by default
                    }
                ],
                "global_settings": {
                    "max_concurrent_sources": 3,
                    "error_threshold": 5,
                    "backoff_multiplier": 2,
                    "max_backoff_hours": 24,
                    "notification_webhook": null
                }
            }
            
            # Save default configuration
            config_path.parent.mkdir(exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(self.schedule_config, f, indent=2)
    
    async def process_scheduled_sources(self, source_names: List[str]):
        """Process a list of sources"""
        logger.info(f"📥 Processing scheduled sources: {', '.join(source_names)}")
        
        processed_count = 0
        error_count = 0
        
        # Find matching sources in pipeline
        sources_to_process = [
            source for source in self.pipeline.sources 
            if source.name in source_names and source.enabled
        ]
        
        if not sources_to_process:
            logger.warning(f"No enabled sources found matching: {source_names}")
            return
        
        # Process sources with concurrency limit
        semaphore = asyncio.Semaphore(self.schedule_config['global_settings']['max_concurrent_sources'])
        
        async def process_source_with_semaphore(source):
            async with semaphore:
                try:
                    count = await self.pipeline.process_source(source)
                    return count, 0  # count, errors
                except Exception as e:
                    logger.error(f"Error processing source {source.name}: {e}")
                    return 0, 1  # count, errors
        
        # Process all sources concurrently
        tasks = [process_source_with_semaphore(source) for source in sources_to_process]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                error_count += 1
            else:
                count, errors = result
                processed_count += count
                error_count += errors
        
        # Log results
        logger.info(f"✅ Scheduled ingestion completed: {processed_count} items processed, {error_count} errors")
        
        # Update statistics
        await self.update_ingestion_stats(source_names, processed_count, error_count)
        
        # Send notifications if configured
        if self.schedule_config['global_settings'].get('notification_webhook'):
            await self.send_notification(source_names, processed_count, error_count)
    
    async def update_ingestion_stats(self, source_names: List[str], processed: int, errors: int):
        """Update ingestion statistics"""
        stats = {
            'timestamp': datetime.utcnow().isoformat(),
            'sources': source_names,
            'processed_count': processed,
            'error_count': errors,
            'schedule_type': 'automated'
        }
        
        # Store in Redis for monitoring
        try:
            stats_key = f"ingestion_stats:{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            self.pipeline.redis_client.set(stats_key, json.dumps(stats), ex=86400)  # 24 hour expiry
            
            # Update rolling statistics
            self.pipeline.redis_client.lpush("ingestion_history", json.dumps(stats))
            self.pipeline.redis_client.ltrim("ingestion_history", 0, 99)  # Keep last 100 entries
            
        except Exception as e:
            logger.warning(f"Failed to update stats in Redis: {e}")
    
    async def send_notification(self, source_names: List[str], processed: int, errors: int):
        """Send notification webhook"""
        webhook_url = self.schedule_config['global_settings']['notification_webhook']
        
        if not webhook_url:
            return
        
        payload = {
            'text': f"PAKE+ Ingestion Report",
            'attachments': [
                {
                    'color': 'good' if errors == 0 else 'warning',
                    'fields': [
                        {'title': 'Sources', 'value': ', '.join(source_names), 'short': True},
                        {'title': 'Processed', 'value': str(processed), 'short': True},
                        {'title': 'Errors', 'value': str(errors), 'short': True},
                        {'title': 'Timestamp', 'value': datetime.utcnow().isoformat(), 'short': True}
                    ]
                }
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("✅ Notification sent successfully")
                    else:
                        logger.warning(f"⚠️ Notification failed: {response.status}")
        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")
    
    def setup_schedules(self):
        """Set up automated schedules"""
        logger.info("⏰ Setting up ingestion schedules...")
        
        schedule.clear()  # Clear any existing schedules
        
        for schedule_config in self.schedule_config['schedules']:
            if not schedule_config['enabled']:
                continue
            
            frequency = schedule_config['frequency']
            sources = schedule_config['sources']
            
            # Parse frequency and create schedule
            if frequency == "every_hour":
                schedule.every().hour.do(self._run_async_job, sources)
            elif frequency == "every_2_hours":
                schedule.every(2).hours.do(self._run_async_job, sources)
            elif frequency == "every_4_hours":
                schedule.every(4).hours.do(self._run_async_job, sources)
            elif frequency == "every_30_minutes":
                schedule.every(30).minutes.do(self._run_async_job, sources)
            elif frequency.startswith("daily_at_"):
                time_str = frequency.split("_")[-1]
                schedule.every().day.at(time_str).do(self._run_async_job, sources)
            elif frequency.startswith("every_") and frequency.endswith("_minutes"):
                minutes = int(frequency.split("_")[1])
                schedule.every(minutes).minutes.do(self._run_async_job, sources)
            elif frequency.startswith("every_") and frequency.endswith("_hours"):
                hours = int(frequency.split("_")[1])
                schedule.every(hours).hours.do(self._run_async_job, sources)
            
            logger.info(f"📅 Scheduled '{schedule_config['name']}' - {frequency}")
        
        logger.info("✅ All schedules configured")
    
    def _run_async_job(self, sources):
        """Wrapper to run async job from sync scheduler"""
        if not self.running:
            return
        
        # Run the async job in the event loop
        asyncio.create_task(self.process_scheduled_sources(sources))
    
    async def run_continuous(self):
        """Run continuous scheduling"""
        self.running = True
        logger.info("🔄 Starting continuous ingestion scheduling...")
        
        # Set up schedules
        self.setup_schedules()
        
        # Run schedule checker
        while self.running:
            try:
                schedule.run_pending()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in schedule runner: {e}")
                await asyncio.sleep(60)
    
    async def stop(self):
        """Stop the orchestrator"""
        logger.info("🛑 Stopping ingestion orchestrator...")
        self.running = False
        
        if self.pipeline:
            await self.pipeline.close()
    
    async def get_schedule_status(self) -> Dict[str, Any]:
        """Get current schedule status"""
        status = {
            'running': self.running,
            'schedules': [],
            'next_runs': [],
            'statistics': await self.get_ingestion_statistics()
        }
        
        # Get schedule information
        for schedule_config in self.schedule_config['schedules']:
            status['schedules'].append({
                'name': schedule_config['name'],
                'sources': schedule_config['sources'],
                'frequency': schedule_config['frequency'],
                'enabled': schedule_config['enabled']
            })
        
        # Get next run times
        for job in schedule.jobs:
            status['next_runs'].append({
                'job': str(job.job_func),
                'next_run': job.next_run.isoformat() if job.next_run else None
            })
        
        return status
    
    async def get_ingestion_statistics(self) -> Dict[str, Any]:
        """Get ingestion statistics from Redis"""
        try:
            # Get recent ingestion history
            history_raw = self.pipeline.redis_client.lrange("ingestion_history", 0, 9)
            history = [json.loads(entry) for entry in history_raw]
            
            # Calculate totals
            total_processed = sum(entry['processed_count'] for entry in history)
            total_errors = sum(entry['error_count'] for entry in history)
            
            # Get unique sources
            unique_sources = set()
            for entry in history:
                unique_sources.update(entry['sources'])
            
            return {
                'total_processed_24h': total_processed,
                'total_errors_24h': total_errors,
                'unique_sources_24h': list(unique_sources),
                'recent_runs': history[:5],  # Last 5 runs
                'success_rate': (total_processed / (total_processed + total_errors)) * 100 if (total_processed + total_errors) > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

# REST API for orchestrator management
from fastapi import FastAPI, HTTPException

app = FastAPI(title="PAKE+ Ingestion Orchestrator API")
orchestrator = IngestionOrchestrator()

@app.on_event("startup")
async def startup():
    await orchestrator.initialize()

@app.on_event("shutdown") 
async def shutdown():
    await orchestrator.stop()

@app.get("/status")
async def get_status():
    """Get orchestrator status"""
    return await orchestrator.get_schedule_status()

@app.post("/start")
async def start_orchestrator():
    """Start continuous scheduling"""
    if orchestrator.running:
        raise HTTPException(status_code=400, detail="Orchestrator already running")
    
    asyncio.create_task(orchestrator.run_continuous())
    return {"message": "Orchestrator started"}

@app.post("/stop")
async def stop_orchestrator():
    """Stop continuous scheduling"""
    if not orchestrator.running:
        raise HTTPException(status_code=400, detail="Orchestrator not running")
    
    await orchestrator.stop()
    return {"message": "Orchestrator stopped"}

@app.post("/run/{schedule_name}")
async def run_schedule_now(schedule_name: str):
    """Run a specific schedule immediately"""
    schedule_config = next(
        (s for s in orchestrator.schedule_config['schedules'] if s['name'] == schedule_name),
        None
    )
    
    if not schedule_config:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    asyncio.create_task(orchestrator.process_scheduled_sources(schedule_config['sources']))
    return {"message": f"Schedule '{schedule_name}' triggered"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
```

### 4.2 Ingestion Schedule Configuration

```json
{
  "schedules": [
    {
      "name": "High Priority RSS",
      "sources": ["ArXiv AI Research", "OpenAI Blog", "Anthropic News"],
      "frequency": "every_hour",
      "enabled": true,
      "priority": "high",
      "max_items_per_run": 20
    },
    {
      "name": "News Feeds",
      "sources": ["Hacker News - AI", "MIT Technology Review AI"],
      "frequency": "every_2_hours",
      "enabled": true,
      "priority": "medium",
      "max_items_per_run": 15
    },
    {
      "name": "Community Sources",
      "sources": ["Reddit r/MachineLearning", "Medium AI Publications"],
      "frequency": "every_4_hours",
      "enabled": true,
      "priority": "low",
      "max_items_per_run": 10
    },
    {
      "name": "Email Processing",
      "sources": ["Gmail Important"],
      "frequency": "every_30_minutes",
      "enabled": false,
      "priority": "high",
      "max_items_per_run": 5
    },
    {
      "name": "File System Scan",
      "sources": ["Personal Documents"],
      "frequency": "daily_at_02:00",
      "enabled": false,
      "priority": "low",
      "max_items_per_run": 50
    },
    {
      "name": "Weekly Deep Scan",
      "sources": ["all_enabled"],
      "frequency": "weekly_sunday_at_01:00",
      "enabled": true,
      "priority": "maintenance",
      "max_items_per_run": 100,
      "full_reprocess": true
    }
  ],
  "global_settings": {
    "max_concurrent_sources": 3,
    "error_threshold": 5,
    "backoff_multiplier": 2,
    "max_backoff_hours": 24,
    "notification_webhook": null,
    "rate_limiting": {
      "requests_per_minute": 60,
      "burst_limit": 10
    },
    "content_filters": {
      "min_content_length": 100,
      "max_content_length": 50000,
      "exclude_patterns": ["advertisement", "sponsored content"],
      "require_patterns": [],
      "language_filter": "en"
    },
    "quality_thresholds": {
      "min_confidence_score": 0.3,
      "auto_verify_threshold": 0.8,
      "reject_threshold": 0.1
    },
    "storage_settings": {
      "max_items_per_source": 1000,
      "retention_days": 365,
      "auto_archive_threshold": 0.2
    }
  },
  "monitoring": {
    "health_check_interval": 300,
    "performance_tracking": true,
    "error_reporting": {
      "email_alerts": false,
      "webhook_url": null,
      "error_threshold": 10
    },
    "metrics_retention_days": 30
  }
}
```

---

## 5. Quality Assurance & Validation Automation

### 5.1 Automated Quality Assurance Pipeline

```python
#!/usr/bin/env python3
# File: scripts/qa_automation.py

import asyncio
import asyncpg
import json
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import re

from confidence_engine import ConfidenceScorer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QualityAssurancePipeline:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'port': 5433,
            'database': 'pake_knowledge',
            'user': 'pake_admin',
            'REDACTED_SECRET': 'process.env.PAKE_HARDCODED_PASSWORD || 'SECURE_HARDCODED_PASSWORD_REQUIRED''
        }
        self.confidence_scorer = ConfidenceScorer()
        self.qa_rules = self.load_qa_rules()
        
    def load_qa_rules(self) -> Dict[str, Any]:
        """Load quality assurance rules"""
        rules_path = Path("configs/qa_rules.json")
        
        if rules_path.exists():
            with open(rules_path, 'r') as f:
                return json.load(f)
        
        # Default QA rules
        default_rules = {
            "validation_rules": {
                "required_fields": [
                    "pake_id", "content", "confidence_score", 
                    "verification_status", "source_uri"
                ],
                "content_constraints": {
                    "min_length": 50,
                    "max_length": 50000,
                    "forbidden_patterns": [
                        r"click here",
                        r"buy now",
                        r"limited time offer"
                    ],
                    "required_patterns": []
                },
                "confidence_constraints": {
                    "min_score": 0.0,
                    "max_score": 1.0,
                    "auto_reject_threshold": 0.1,
                    "auto_verify_threshold": 0.9
                }
            },
            "quality_checks": {
                "duplicate_detection": {
                    "enabled": true,
                    "similarity_threshold": 0.85,
                    "title_similarity_threshold": 0.9
                },
                "language_detection": {
                    "enabled": true,
                    "supported_languages": ["en"],
                    "confidence_threshold": 0.7
                },
                "spam_detection": {
                    "enabled": true,
                    "spam_keywords": [
                        "spam", "advertisement", "promotion",
                        "click here", "buy now", "limited offer"
                    ],
                    "max_spam_score": 0.3
                },
                "broken_links": {
                    "enabled": true,
                    "check_external_links": true,
                    "timeout_seconds": 10
                }
            },
            "automated_actions": {
                "auto_reject_spam": true,
                "auto_verify_high_confidence": true,
                "auto_flag_duplicates": true,
                "auto_update_confidence": true,
                "quarantine_suspicious": true
            },
            "scheduling": {
                "full_scan_interval_hours": 24,
                "incremental_scan_interval_minutes": 30,
                "priority_scan_interval_minutes": 5
            }
        }
        
        # Save default rules
        rules_path.parent.mkdir(exist_ok=True)
        with open(rules_path, 'w') as f:
            json.dump(default_rules, f, indent=2)
        
        return default_rules
    
    async def validate_knowledge_item(self, item: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Validate a single knowledge item"""
        errors = []
        warnings = []
        metadata = {}
        
        # Check required fields
        for field in self.qa_rules["validation_rules"]["required_fields"]:
            if field not in item or item[field] is None:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return False, errors, metadata
        
        # Content validation
        content = item.get('content', '')
        content_constraints = self.qa_rules["validation_rules"]["content_constraints"]
        
        if len(content) < content_constraints["min_length"]:
            errors.append(f"Content too short: {len(content)} < {content_constraints['min_length']}")
        
        if len(content) > content_constraints["max_length"]:
            warnings.append(f"Content very long: {len(content)} > {content_constraints['max_length']}")
        
        # Check forbidden patterns
        for pattern in content_constraints["forbidden_patterns"]:
            if re.search(pattern, content, re.IGNORECASE):
                errors.append(f"Content contains forbidden pattern: {pattern}")
        
        # Confidence score validation
        confidence = item.get('confidence_score', 0.0)
        conf_constraints = self.qa_rules["validation_rules"]["confidence_constraints"]
        
        if not (conf_constraints["min_score"] <= confidence <= conf_constraints["max_score"]):
            errors.append(f"Invalid confidence score: {confidence}")
        
        # Quality checks
        qa_results = await self.run_quality_checks(item)
        metadata.update(qa_results)
        
        # Determine if item passes validation
        is_valid = len(errors) == 0
        
        return is_valid, errors + warnings, metadata
    
    async def run_quality_checks(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Run quality checks on knowledge item"""
        results = {}
        quality_config = self.qa_rules["quality_checks"]
        
        # Duplicate detection
        if quality_config["duplicate_detection"]["enabled"]:
            duplicate_info = await self.check_duplicates(item)
            results["duplicate_check"] = duplicate_info
        
        # Language detection
        if quality_config["language_detection"]["enabled"]:
            language_info = await self.detect_language(item)
            results["language_check"] = language_info
        
        # Spam detection
        if quality_config["spam_detection"]["enabled"]:
            spam_info = await self.detect_spam(item)
            results["spam_check"] = spam_info
        
        # Broken links check
        if quality_config["broken_links"]["enabled"]:
            links_info = await self.check_links(item)
            results["links_check"] = links_info
        
        return results
    
    async def check_duplicates(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Check for duplicate content"""
        try:
            conn = await asyncpg.connect(**self.db_config)
            
            # Simple duplicate check based on title similarity
            similar_items = await conn.fetch("""
                SELECT pake_id, content, 
                       similarity(content, $1) as content_similarity
                FROM knowledge_nodes 
                WHERE pake_id != $2
                AND similarity(content, $1) > $3
                ORDER BY content_similarity DESC
                LIMIT 5
            """, item['content'], item.get('pake_id', ''), 0.7)
            
            await conn.close()
            
            duplicates = []
            for row in similar_items:
                duplicates.append({
                    'pake_id': row['pake_id'],
                    'similarity': float(row['content_similarity'])
                })
            
            threshold = self.qa_rules["quality_checks"]["duplicate_detection"]["similarity_threshold"]
            has_duplicates = any(d['similarity'] > threshold for d in duplicates)
            
            return {
                'has_duplicates': has_duplicates,
                'similar_items': duplicates,
                'max_similarity': max([d['similarity'] for d in duplicates]) if duplicates else 0
            }
            
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")
            return {'has_duplicates': False, 'error': str(e)}
    
    async def detect_language(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Detect content language"""
        try:
            # Simple language detection (could use langdetect library)
            content = item.get('content', '')
            
            # Basic heuristic: check for common English words
            english_indicators = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
            word_count = len(content.split())
            english_word_count = sum(1 for word in content.lower().split() if word in english_indicators)
            
            english_ratio = english_word_count / word_count if word_count > 0 else 0
            
            is_english = english_ratio > 0.1  # At least 10% common English words
            
            return {
                'detected_language': 'en' if is_english else 'unknown',
                'confidence': english_ratio,
                'is_supported': is_english
            }
            
        except Exception as e:
            return {'detected_language': 'unknown', 'error': str(e)}
    
    async def detect_spam(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Detect spam content"""
        try:
            content = item.get('content', '').lower()
            spam_keywords = self.qa_rules["quality_checks"]["spam_detection"]["spam_keywords"]
            
            spam_count = sum(1 for keyword in spam_keywords if keyword.lower() in content)
            spam_score = spam_count / len(spam_keywords) if spam_keywords else 0
            
            max_spam_score = self.qa_rules["quality_checks"]["spam_detection"]["max_spam_score"]
            is_spam = spam_score > max_spam_score
            
            return {
                'is_spam': is_spam,
                'spam_score': spam_score,
                'detected_keywords': [kw for kw in spam_keywords if kw.lower() in content]
            }
            
        except Exception as e:
            return {'is_spam': False, 'error': str(e)}
    
    async def check_links(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Check for broken links in content"""
        try:
            import aiohttp
            
            content = item.get('content', '')
            
            # Extract URLs from content
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, content)
            
            if not urls:
                return {'total_links': 0, 'broken_links': 0, 'working_links': 0}
            
            broken_links = []
            working_links = []
            
            timeout = self.qa_rules["quality_checks"]["broken_links"]["timeout_seconds"]
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                for url in urls:
                    try:
                        async with session.head(url) as response:
                            if response.status < 400:
                                working_links.append(url)
                            else:
                                broken_links.append({'url': url, 'status': response.status})
                    except Exception as e:
                        broken_links.append({'url': url, 'error': str(e)})
            
            return {
                'total_links': len(urls),
                'working_links': len(working_links),
                'broken_links': len(broken_links),
                'broken_link_details': broken_links
            }
            
        except Exception as e:
            return {'total_links': 0, 'error': str(e)}
    
    async def run_automated_actions(self, item: Dict[str, Any], validation_result: Dict[str, Any]):
        """Run automated actions based on validation results"""
        actions_taken = []
        automated_config = self.qa_rules["automated_actions"]
        
        try:
            conn = await asyncpg.connect(**self.db_config)
            
            pake_id = item.get('pake_id')
            if not pake_id:
                return actions_taken
            
            # Auto-reject spam
            if (automated_config["auto_reject_spam"] and 
                validation_result.get('spam_check', {}).get('is_spam', False)):
                
                await conn.execute("""
                    UPDATE knowledge_nodes 
                    SET verification_status = 'rejected', 
                        metadata = metadata || $2
                    WHERE pake_id = $1
                """, pake_id, json.dumps({'auto_rejected': 'spam_detected'}))
                
                actions_taken.append("auto_rejected_spam")
            
            # Auto-verify high confidence
            elif (automated_config["auto_verify_high_confidence"] and 
                  item.get('confidence_score', 0) >= self.qa_rules["validation_rules"]["confidence_constraints"]["auto_verify_threshold"]):
                
                await conn.execute("""
                    UPDATE knowledge_nodes 
                    SET verification_status = 'verified'
                    WHERE pake_id = $1 AND verification_status = 'pending'
                """, pake_id)
                
                actions_taken.append("auto_verified_high_confidence")
            
            # Flag duplicates
            if (automated_config["auto_flag_duplicates"] and 
                validation_result.get('duplicate_check', {}).get('has_duplicates', False)):
                
                await conn.execute("""
                    UPDATE knowledge_nodes 
                    SET metadata = metadata || $2
                    WHERE pake_id = $1
                """, pake_id, json.dumps({'flagged': 'potential_duplicate'}))
                
                actions_taken.append("flagged_duplicate")
            
            # Update confidence score
            if automated_config["auto_update_confidence"]:
                new_confidence = self.confidence_scorer.calculate_confidence(item)
                
                await conn.execute("""
                    UPDATE knowledge_nodes 
                    SET confidence_score = $2
                    WHERE pake_id = $1
                """, pake_id, new_confidence)
                
                actions_taken.append(f"updated_confidence_to_{new_confidence}")
            
            await conn.close()
            
        except Exception as e:
            logger.error(f"Error running automated actions: {e}")
            actions_taken.append(f"error: {str(e)}")
        
        return actions_taken
    
    async def scan_pending_items(self):
        """Scan all pending items for quality issues"""
        logger.info("🔍 Starting QA scan of pending items...")
        
        try:
            conn = await asyncpg.connect(**self.db_config)
            
            # Get all pending items
            pending_items = await conn.fetch("""
                SELECT pake_id, content, confidence_score, verification_status, 
                       source_uri, metadata, tags
                FROM knowledge_nodes 
                WHERE verification_status = 'pending'
                ORDER BY created_at DESC
            """)
            
            await conn.close()
            
            logger.info(f"Found {len(pending_items)} pending items to validate")
            
            processed_count = 0
            error_count = 0
            
            for row in pending_items:
                try:
                    item = dict(row)
                    
                    # Run validation
                    is_valid, issues, qa_metadata = await self.validate_knowledge_item(item)
                    
                    # Run automated actions
                    actions = await self.run_automated_actions(item, qa_metadata)
                    
                    # Log results
                    if not is_valid:
                        logger.warning(f"Item {item['pake_id']} failed validation: {issues}")
                        error_count += 1
                    else:
                        logger.debug(f"Item {item['pake_id']} passed validation")
                    
                    if actions:
                        logger.info(f"Automated actions for {item['pake_id']}: {actions}")
                    
                    processed_count += 1
                    
                    # Small delay to prevent overwhelming the system
                    if processed_count % 10 == 0:
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"Error processing item {row.get('pake_id', 'unknown')}: {e}")
                    error_count += 1
            
            logger.info(f"✅ QA scan completed: {processed_count} processed, {error_count} errors")
            
            return {
                'processed': processed_count,
                'errors': error_count,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in QA scan: {e}")
            return {'error': str(e)}
    
    async def generate_qa_report(self) -> Dict[str, Any]:
        """Generate quality assurance report"""
        try:
            conn = await asyncpg.connect(**self.db_config)
            
            # Get overall statistics
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_items,
                    COUNT(*) FILTER (WHERE verification_status = 'verified') as verified_items,
                    COUNT(*) FILTER (WHERE verification_status = 'pending') as pending_items,
                    COUNT(*) FILTER (WHERE verification_status = 'rejected') as rejected_items,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(*) FILTER (WHERE confidence_score >= 0.8) as high_confidence_items,
                    COUNT(*) FILTER (WHERE confidence_score < 0.4) as low_confidence_items
                FROM knowledge_nodes
            """)
            
            # Get recent quality issues
            recent_issues = await conn.fetch("""
                SELECT pake_id, metadata, created_at
                FROM knowledge_nodes
                WHERE metadata ? 'flagged' OR verification_status = 'rejected'
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            await conn.close()
            
            report = {
                'timestamp': datetime.utcnow().isoformat(),
                'statistics': dict(stats),
                'recent_issues': [
                    {
                        'pake_id': row['pake_id'],
                        'issue': row['metadata'].get('flagged') or 'rejected',
                        'created_at': row['created_at'].isoformat()
                    }
                    for row in recent_issues
                ],
                'quality_score': (stats['verified_items'] / stats['total_items']) * 100 if stats['total_items'] > 0 else 0,
                'recommendations': self._generate_recommendations(dict(stats))
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating QA report: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on statistics"""
        recommendations = []
        
        if stats['pending_items'] > 100:
            recommendations.append("High number of pending items - consider increasing validation frequency")
        
        if stats['avg_confidence'] < 0.6:
            recommendations.append("Low average confidence score - review ingestion sources quality")
        
        if stats['low_confidence_items'] > stats['total_items'] * 0.2:
            recommendations.append("High percentage of low-confidence items - adjust confidence scoring weights")
        
        if stats['rejected_items'] > stats['total_items'] * 0.1:
            recommendations.append("High rejection rate - review QA rules and ingestion filters")
        
        return recommendations
    
    async def run_continuous_qa(self):
        """Run continuous quality assurance"""
        logger.info("🔄 Starting continuous QA monitoring...")
        
        schedule_config = self.qa_rules["scheduling"]
        
        last_full_scan = datetime.utcnow()
        last_incremental_scan = datetime.utcnow()
        
        while True:
            try:
                now = datetime.utcnow()
                
                # Check if it's time for a full scan
                if (now - last_full_scan).total_seconds() >= schedule_config["full_scan_interval_hours"] * 3600:
                    logger.info("🔍 Running full QA scan...")
                    await self.scan_pending_items()
                    last_full_scan = now
                
                # Check if it's time for an incremental scan
                elif (now - last_incremental_scan).total_seconds() >= schedule_config["incremental_scan_interval_minutes"] * 60:
                    logger.info("🔄 Running incremental QA scan...")
                    # Scan only recent items
                    await self.scan_recent_items()
                    last_incremental_scan = now
                
                # Sleep until next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in continuous QA: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def scan_recent_items(self):
        """Scan only recently added items"""
        logger.debug("Scanning recent items...")
        
        try:
            conn = await asyncpg.connect(**self.db_config)
            
            # Get items from last 30 minutes
            recent_items = await conn.fetch("""
                SELECT pake_id, content, confidence_score, verification_status, 
                       source_uri, metadata, tags
                FROM knowledge_nodes 
                WHERE created_at > NOW() - INTERVAL '30 minutes'
                AND verification_status = 'pending'
            """)
            
            await conn.close()
            
            if recent_items:
                logger.info(f"Found {len(recent_items)} recent items to validate")
                
                for row in recent_items:
                    item = dict(row)
                    is_valid, issues, qa_metadata = await self.validate_knowledge_item(item)
                    actions = await self.run_automated_actions(item, qa_metadata)
                    
                    if actions:
                        logger.debug(f"Automated actions for {item['pake_id']}: {actions}")
            
        except Exception as e:
            logger.error(f"Error in recent items scan: {e}")

# CLI interface
async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='PAKE+ Quality Assurance Pipeline')
    parser.add_argument('command', choices=['scan', 'report', 'monitor', 'validate'])
    parser.add_argument('--pake-id', help='Specific item to validate')
    parser.add_argument('--output', help='Output file for report')
    
    args = parser.parse_args()
    
    qa_pipeline = QualityAssurancePipeline()
    
    if args.command == 'scan':
        result = await qa_pipeline.scan_pending_items()
        print(json.dumps(result, indent=2))
    
    elif args.command == 'report':
        report = await qa_pipeline.generate_qa_report()
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to {args.output}")
        else:
            print(json.dumps(report, indent=2))
    
    elif args.command == 'monitor':
        await qa_pipeline.run_continuous_qa()
    
    elif args.command == 'validate' and args.pake_id:
        # Validate specific item
        conn = await asyncpg.connect(**qa_pipeline.db_config)
        item_data = await conn.fetchrow("""
            SELECT pake_id, content, confidence_score, verification_status, 
                   source_uri, metadata, tags
            FROM knowledge_nodes 
            WHERE pake_id = $1
        """, args.pake_id)
        await conn.close()
        
        if item_data:
            item = dict(item_data)
            is_valid, issues, qa_metadata = await qa_pipeline.validate_knowledge_item(item)
            
            result = {
                'pake_id': args.pake_id,
                'valid': is_valid,
                'issues': issues,
                'qa_metadata': qa_metadata
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Item not found: {args.pake_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. Monitoring & Alerting Automation

### 6.1 Comprehensive Monitoring System

```python
#!/usr/bin/env python3
# File: scripts/monitoring_system.py

import asyncio
import aiohttp
import json
import logging
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import psutil
import asyncpg
import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class HealthCheck:
    service_name: str
    check_type: str  # 'http', 'tcp', 'process', 'database'
    endpoint: str
    expected_response: Optional[str] = None
    timeout_seconds: int = 10
    critical: bool = True

@dataclass
class Alert:
    alert_id: str
    service_name: str
    severity: str  # 'critical', 'warning', 'info'
    message: str
    timestamp: datetime
    resolved: bool = False
    metadata: Dict[str, Any] = None

class MonitoringSystem:
    def __init__(self):
        self.health_checks = [
            HealthCheck("PostgreSQL", "tcp", "localhost:5433", critical=True),
            HealthCheck("Redis", "tcp", "localhost:6380", critical=True),
            HealthCheck("MCP Server", "http", "http://localhost:8000/health", critical=True),
            HealthCheck("API Bridge", "http", "http://localhost:3000/health", critical=True),
            HealthCheck("n8n", "http", "http://localhost:5678", critical=False),
            HealthCheck("Ingestion Manager", "http", "http://localhost:8001", critical=False),
        ]
        
        self.alerts = []
        self.alert_history = []
        self.metrics_history = []
        
        # Alert configuration
        self.alert_config = {
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'REDACTED_SECRET': '',
                'recipients': []
            },
            'webhook': {
                'enabled': False,
                'url': '',
                'headers': {}
            },
            'thresholds': {
                'cpu_usage': 80,
                'memory_usage': 85,
                'disk_usage': 90,
                'response_time': 5000,  # milliseconds
                'error_rate': 10  # percentage
            }
        }
        
        self.load_config()
    
    def load_config(self):
        """Load monitoring configuration"""
        try:
            from pathlib import Path
            config_path = Path("configs/monitoring.json")
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.alert_config.update(config)
        except Exception as e:
            logger.warning(f"Could not load monitoring config: {e}")
    
    async def check_service_health(self, health_check: HealthCheck) -> Dict[str, Any]:
        """Check health of a specific service"""
        start_time = time.time()
        
        try:
            if health_check.check_type == "http":
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        health_check.endpoint, 
                        timeout=aiohttp.ClientTimeout(total=health_check.timeout_seconds)
                    ) as response:
                        response_time = (time.time() - start_time) * 1000
                        
                        return {
                            'service': health_check.service_name,
                            'healthy': response.status < 400,
                            'status_code': response.status,
                            'response_time_ms': response_time,
                            'timestamp': datetime.utcnow().isoformat()
                        }
            
            elif health_check.check_type == "tcp":
                host, port = health_check.endpoint.split(':')
                port = int(port)
                
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=health_check.timeout_seconds
                )
                writer.close()
                await writer.wait_closed()
                
                response_time = (time.time() - start_time) * 1000
                
                return {
                    'service': health_check.service_name,
                    'healthy': True,
                    'response_time_ms': response_time,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            elif health_check.check_type == "database":
                # Specific database health check
                if "postgresql" in health_check.service_name.lower():
                    return await self.check_postgresql_health()
                elif "redis" in health_check.service_name.lower():
                    return await self.check_redis_health()
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            return {
                'service': health_check.service_name,
                'healthy': False,
                'error': str(e),
                'response_time_ms': response_time,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def check_postgresql_health(self) -> Dict[str, Any]:
        """Detailed PostgreSQL health check"""
        try:
            conn = await asyncpg.connect(
                host='localhost',
                port=5433,
                database='pake_knowledge',
                user='pake_admin',
                REDACTED_SECRET='process.env.PAKE_HARDCODED_PASSWORD || 'SECURE_HARDCODED_PASSWORD_REQUIRED''SECURE_DB_PASSWORD_REQUIRED''
            )
            
            # Check basic connectivity
            result = await conn.fetchval("SELECT 1")
            
            # Check table count
            table_count = await conn.fetchval("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            # Check record count
            record_count = await conn.fetchval("SELECT COUNT(*) FROM knowledge_nodes")
            
            # Check recent activity
            recent_activity = await conn.fetchval("""
                SELECT COUNT(*) FROM knowledge_nodes 
                WHERE created_at > NOW() - INTERVAL '1 hour'
            """)
            
            await conn.close()
            
            return {
                'service': 'PostgreSQL',
                'healthy': True,
                'tables': table_count,
                'records': record_count,
                'recent_activity': recent_activity,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'service': 'PostgreSQL',
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def check_redis_health(self) -> Dict[str, Any]:
        """Detailed Redis health check"""
        try:
            r = redis.Redis(host='localhost', port=6380, decode_responses=True)
            
            # Check basic connectivity
            r.ping()
            
            # Get info
            info = r.info()
            
            return {
                'service': 'Redis',
                'healthy': True,
                'memory_usage': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'uptime_seconds': info.get('uptime_in_seconds'),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'service': 'Redis',
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'cpu': {
                    'usage_percent': cpu_percent,
                    'count': psutil.cpu_count()
                },
                'memory': {
                    'total_gb': round(memory.total / (1024**3), 2),
                    'used_gb': round(memory.used / (1024**3), 2),
                    'usage_percent': memory.percent,
                    'available_gb': round(memory.available / (1024**3), 2)
                },
                'disk': {
                    'total_gb': round(disk.total / (1024**3), 2),
                    'used_gb': round(disk.used / (1024**3), 2),
                    'usage_percent': round((disk.used / disk.total) * 100, 2),
                    'free_gb': round(disk.free / (1024**3), 2)
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_received': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_received': network.packets_recv
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {'error': str(e)}
    
    async def create_alert(self, service_name: str, severity: str, message: str, metadata: Dict[str, Any] = None):
        """Create a new alert"""
        alert = Alert(
            alert_id=f"{service_name}_{int(time.time())}",
            service_name=service_name,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.alerts.append(alert)
        logger.warning(f"ALERT [{severity.upper()}] {service_name}: {message}")
        
        # Send notifications
        await self.send_alert_notification(alert)
        
        return alert
    
    async def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                self.alert_history.append(alert)
                self.alerts.remove(alert)
                
                logger.info(f"RESOLVED: Alert {alert_id}")
                break
    
    async def send_alert_notification(self, alert: Alert):
        """Send alert notification via configured channels"""
        try:
            # Email notification
            if self.alert_config['email']['enabled']:
                await self.send_email_alert(alert)
            
            # Webhook notification
            if self.alert_config['webhook']['enabled']:
                await self.send_webhook_alert(alert)
                
        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")
    
    async def send_email_alert(self, alert: Alert):
        """Send email alert"""
        try:
            email_config = self.alert_config['email']
            
            msg = MIMEMultipart()
            msg['From'] = email_config['username']
            msg['To'] = ', '.join(email_config['recipients'])
            msg['Subject'] = f"PAKE+ Alert [{alert.severity.upper()}]: {alert.service_name}"
            
            body = f"""
            PAKE+ System Alert
            
            Service: {alert.service_name}
            Severity: {alert.severity.upper()}
            Message: {alert.message}
            Timestamp: {alert.timestamp.isoformat()}
            
            Alert ID: {alert.alert_id}
            
            Metadata:
            {json.dumps(alert.metadata, indent=2)}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['REDACTED_SECRET'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent for {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
    
    async def send_webhook_alert(self, alert: Alert):
        """Send webhook alert"""
        try:
            webhook_config = self.alert_config['webhook']
            
            payload = {
                'alert_id': alert.alert_id,
                'service': alert.service_name,
                'severity': alert.severity,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'metadata': alert.metadata
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_config['url'],
                    json=payload,
                    headers=webhook_config.get('headers', {})
                ) as response:
                    if response.status == 200:
                        logger.info(f"Webhook alert sent for {alert.alert_id}")
                    else:
                        logger.error(f"Webhook alert failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending webhook alert: {e}")
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = []
        
        # Service health checks
        for health_check in self.health_checks:
            result = await self.check_service_health(health_check)
            results.append(result)
            
            # Check for alerts
            if not result['healthy'] and health_check.critical:
                # Check if alert already exists
                existing_alert = any(
                    alert.service_name == health_check.service_name and not alert.resolved
                    for alert in self.alerts
                )
                
                if not existing_alert:
                    await self.create_alert(
                        health_check.service_name,
                        'critical',
                        f"Service health check failed: {result.get('error', 'Unknown error')}",
                        result
                    )
            
            # Resolve alert if service is healthy again
            elif result['healthy']:
                for alert in self.alerts.copy():
                    if alert.service_name == health_check.service_name and not alert.resolved:
                        await self.resolve_alert(alert.alert_id)
        
        # System metrics
        system_metrics = self.get_system_metrics()
        
        # Check system thresholds
        if 'cpu' in system_metrics:
            cpu_usage = system_metrics['cpu']['usage_percent']
            if cpu_usage > self.alert_config['thresholds']['cpu_usage']:
                await self.create_alert(
                    'System',
                    'warning',
                    f"High CPU usage: {cpu_usage}%",
                    {'cpu_usage': cpu_usage}
                )
        
        if 'memory' in system_metrics:
            memory_usage = system_metrics['memory']['usage_percent']
            if memory_usage > self.alert_config['thresholds']['memory_usage']:
                await self.create_alert(
                    'System',
                    'warning',
                    f"High memory usage: {memory_usage}%",
                    {'memory_usage': memory_usage}
                )
        
        if 'disk' in system_metrics:
            disk_usage = system_metrics['disk']['usage_percent']
            if disk_usage > self.alert_config['thresholds']['disk_usage']:
                await self.create_alert(
                    'System',
                    'critical',
                    f"High disk usage: {disk_usage}%",
                    {'disk_usage': disk_usage}
                )
        
        # Store metrics history
        self.metrics_history.append(system_metrics)
        
        # Keep only last 24 hours of metrics (assuming 5 minute intervals)
        if len(self.metrics_history) > 288:
            self.metrics_history = self.metrics_history[-288:]
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'service_health': results,
            'system_metrics': system_metrics,
            'active_alerts': len(self.alerts),
            'overall_health': self._calculate_overall_health(results)
        }
    
    def _calculate_overall_health(self, results: List[Dict[str, Any]]) -> str:
        """Calculate overall system health"""
        critical_services = [r for r in results if r.get('service') in ['PostgreSQL', 'Redis', 'MCP Server']]
        critical_healthy = all(r.get('healthy', False) for r in critical_services)
        
        all_healthy = all(r.get('healthy', False) for r in results)
        
        if critical_healthy and all_healthy:
            return 'healthy'
        elif critical_healthy:
            return 'degraded'
        else:
            return 'critical'
    
    async def generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        current_status = await self.run_health_checks()
        
        # Calculate uptime statistics
        healthy_checks = sum(1 for r in current_status['service_health'] if r.get('healthy', False))
        total_checks = len(current_status['service_health'])
        uptime_percentage = (healthy_checks / total_checks) * 100 if total_checks > 0 else 0
        
        # Alert statistics
        alert_stats = {
            'active_alerts': len(self.alerts),
            'resolved_alerts_24h': len([a for a in self.alert_history if (datetime.utcnow() - a.timestamp).days < 1]),
            'critical_alerts': len([a for a in self.alerts if a.severity == 'critical']),
            'warning_alerts': len([a for a in self.alerts if a.severity == 'warning'])
        }
        
        # Performance metrics (last 24 hours)
        if self.metrics_history:
            avg_cpu = sum(m.get('cpu', {}).get('usage_percent', 0) for m in self.metrics_history) / len(self.metrics_history)
            avg_memory = sum(m.get('memory', {}).get('usage_percent', 0) for m in self.metrics_history) / len(self.metrics_history)
            avg_disk = sum(m.get('disk', {}).get('usage_percent', 0) for m in self.metrics_history) / len(self.metrics_history)
        else:
            avg_cpu = avg_memory = avg_disk = 0
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_health': current_status['overall_health'],
            'uptime_percentage': uptime_percentage,
            'current_status': current_status,
            'alert_statistics': alert_stats,
            'performance_averages_24h': {
                'cpu_usage': round(avg_cpu, 2),
                'memory_usage': round(avg_memory, 2),
                'disk_usage': round(avg_disk, 2)
            },
            'active_alerts': [asdict(alert) for alert in self.alerts],
            'recommendations': self._generate_monitoring_recommendations(current_status, alert_stats)
        }
    
    def _generate_monitoring_recommendations(self, status: Dict[str, Any], alert_stats: Dict[str, Any]) -> List[str]:
        """Generate monitoring recommendations"""
        recommendations = []
        
        if status['overall_health'] == 'critical':
            recommendations.append("URGENT: Critical services are down - immediate attention required")
        
        if alert_stats['active_alerts'] > 5:
            recommendations.append("High number of active alerts - review system configuration")
        
        if any(r.get('response_time_ms', 0) > 5000 for r in status['service_health']):
            recommendations.append("Slow response times detected - investigate performance issues")
        
        system_metrics = status.get('system_metrics', {})
        if system_metrics.get('cpu', {}).get('usage_percent', 0) > 80:
            recommendations.append("High CPU usage - consider scaling or optimization")
        
        if system_metrics.get('memory', {}).get('usage_percent', 0) > 85:
            recommendations.append("High memory usage - monitor for memory leaks")
        
        if system_metrics.get('disk', {}).get('usage_percent', 0) > 90:
            recommendations.append("Low disk space - clean up or expand storage")
        
        return recommendations
    
    async def run_continuous_monitoring(self, interval_seconds: int = 300):
        """Run continuous monitoring"""
        logger.info(f"🔍 Starting continuous monitoring (interval: {interval_seconds}s)...")
        
        while True:
            try:
                # Run health checks
                status = await self.run_health_checks()
                
                logger.info(f"Health check completed - Status: {status['overall_health'].upper()}")
                logger.info(f"Services: {len([r for r in status['service_health'] if r.get('healthy')])} healthy / {len(status['service_health'])} total")
                
                if self.alerts:
                    logger.warning(f"Active alerts: {len(self.alerts)}")
                
                # Sleep until next check
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

# Web API for monitoring
from fastapi import FastAPI

monitoring_app = FastAPI(title="PAKE+ Monitoring API")
monitor = MonitoringSystem()

@monitoring_app.get("/health")
async def get_health():
    """Get current health status"""
    return await monitor.run_health_checks()

@monitoring_app.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    return monitor.get_system_metrics()

@monitoring_app.get("/alerts")
async def get_alerts():
    """Get active alerts"""
    return [asdict(alert) for alert in monitor.alerts]

@monitoring_app.get("/report")
async def get_monitoring_report():
    """Get comprehensive monitoring report"""
    return await monitor.generate_monitoring_report()

@monitoring_app.post("/alerts/{alert_id}/resolve")
async def resolve_alert_endpoint(alert_id: str):
    """Resolve an alert"""
    await monitor.resolve_alert(alert_id)
    return {"message": f"Alert {alert_id} resolved"}

# CLI interface
async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='PAKE+ Monitoring System')
    parser.add_argument('command', choices=['check', 'monitor', 'report', 'api'])
    parser.add_argument('--interval', type=int, default=300, help='Monitoring interval in seconds')
    parser.add_argument('--output', help='Output file for report')
    
    args = parser.parse_args()
    
    if args.command == 'check':
        status = await monitor.run_health_checks()
        print(json.dumps(status, indent=2, default=str))
    
    elif args.command == 'monitor':
        await monitor.run_continuous_monitoring(args.interval)
    
    elif args.command == 'report':
        report = await monitor.generate_monitoring_report()
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Report saved to {args.output}")
        else:
            print(json.dumps(report, indent=2, default=str))
    
    elif args.command == 'api':
        import uvicorn
        uvicorn.run(monitoring_app, host="0.0.0.0", port=8003)

if __name__ == "__main__":
    asyncio.run(main())
```

---

This automation guide continues with Backup & Recovery, Maintenance & Optimization, Integration Testing, and Troubleshooting sections. Would you like me to continue with the remaining sections of this comprehensive automation guide?