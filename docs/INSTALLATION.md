# PAKE System Installation Guide

**Version**: 10.1.0  
**Last Updated**: September 14, 2025

This guide provides comprehensive installation instructions for the PAKE (Personal AI Knowledge Engine) System, covering both development and production environments.

## Table of Contents

- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Development Installation](#development-installation)
- [Production Installation](#production-installation)
- [Docker Installation](#docker-installation)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Upgrading](#upgrading)

## System Requirements

### Minimum Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS (10.15+), or Windows 10+
- **Python**: 3.12 or higher
- **Node.js**: 22.18.0 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 10GB free space
- **Network**: Internet connection for API access

### Recommended Requirements

- **Operating System**: Ubuntu 22.04 LTS or macOS 12+
- **Python**: 3.12.3
- **Node.js**: 22.19.0
- **Memory**: 16GB RAM
- **Storage**: 50GB SSD
- **CPU**: 4+ cores
- **Network**: Stable broadband connection

### External Dependencies

- **PostgreSQL**: 14+ (for data storage)
- **Redis**: 6+ (for caching)
- **Neo4j**: 5+ (for knowledge graph, optional)

## Quick Start

For a quick evaluation, you can run the system with minimal setup:

```bash
# Clone the repository
git clone https://github.com/pake-system/pake-system.git
cd pake-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-phase7.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Start the server
python mcp_server_standalone.py
```

The system will be available at `http://localhost:8000`.

## Development Installation

### Step 1: Prerequisites

#### Install Python 3.12+

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev
```

**macOS:**
```bash
brew install python@3.12
```

**Windows:**
Download from [python.org](https://www.python.org/downloads/)

#### Install Node.js 22.18.0+

**Using Node Version Manager (Recommended):**
```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc

# Install Node.js
nvm install 22.18.0
nvm use 22.18.0
```

**Direct Installation:**
- Download from [nodejs.org](https://nodejs.org/)

#### Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Windows:**
Download from [postgresql.org](https://www.postgresql.org/download/windows/)

#### Install Redis

**Ubuntu/Debian:**
```bash
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
Download from [redis.io](https://redis.io/download)

### Step 2: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/pake-system/pake-system.git
cd pake-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements-phase7.txt

# Install Node.js dependencies
npm install
```

### Step 3: Database Setup

#### PostgreSQL Setup

```bash
# Create database user
sudo -u postgres createuser --interactive pake_user
# Enter 'y' when prompted for superuser privileges

# Create database
sudo -u postgres createdb pake_system

# Set REDACTED_SECRET for user
sudo -u postgres psql -c "ALTER USER pake_user PASSWORD 'your_REDACTED_SECRET';"
```

#### Redis Setup

Redis should be running on the default port (6379). Verify with:

```bash
redis-cli ping
# Should return: PONG
```

### Step 4: Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit environment file
nano .env  # or use your preferred editor
```

**Required Environment Variables:**

```bash
# Database Configuration
DATABASE_URL=postgresql://pake_user:your_REDACTED_SECRET@localhost:5432/pake_system
REDIS_URL=redis://localhost:6379/0

# API Keys (Get these from respective services)
FIRECRAWL_API_KEY=fc-your-api-key-here
PUBMED_EMAIL=your-email@example.com

# System Configuration
VAULT_PATH=/path/to/your/obsidian/vault
BRIDGE_PORT=3001
LOG_LEVEL=INFO

# Optional: Neo4j for knowledge graph
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-REDACTED_SECRET
```

### Step 5: Initialize Database

```bash
# Run database migrations
python scripts/setup_database.py

# Create initial data
python scripts/seed_database.py
```

### Step 6: Start Development Services

```bash
# Terminal 1: Start the main server
python mcp_server_standalone.py

# Terminal 2: Start TypeScript bridge (if using Obsidian integration)
cd src/bridge
NODE_PATH=/root/.nvm/versions/node/v22.19.0/lib/node_modules:/usr/local/lib/node_modules \
VAULT_PATH=/path/to/your/vault \
BRIDGE_PORT=3001 \
node obsidian_bridge.js
```

### Step 7: Verify Installation

```bash
# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ml/dashboard

# Run tests
python -m pytest tests/ -v
```

## Production Installation

### Step 1: Server Setup

#### Ubuntu Server 22.04 LTS

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.12 python3.12-venv python3.12-dev \
    postgresql postgresql-contrib redis-server nginx \
    git curl wget build-essential

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Step 2: Application Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash pake
sudo usermod -aG sudo pake

# Switch to application user
sudo su - pake

# Clone repository
git clone https://github.com/pake-system/pake-system.git
cd pake-system

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements-phase7.txt
```

### Step 3: Database Configuration

```bash
# Configure PostgreSQL
sudo -u postgres psql -c "CREATE USER pake WITH PASSWORD 'secure_REDACTED_SECRET';"
sudo -u postgres psql -c "CREATE DATABASE pake_system OWNER pake;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE pake_system TO pake;"

# Configure Redis
sudo nano /etc/redis/redis.conf
# Set: requirepass your_redis_REDACTED_SECRET
sudo systemctl restart redis-server
```

### Step 4: Production Environment

```bash
# Create production environment file
cp .env.production.example .env.production

# Configure production settings
nano .env.production
```

**Production Environment Variables:**

```bash
# Database Configuration
DATABASE_URL=postgresql://pake:secure_REDACTED_SECRET@localhost:5432/pake_system
REDIS_URL=redis://:your_redis_REDACTED_SECRET@localhost:6379/0

# API Keys
FIRECRAWL_API_KEY=fc-your-production-api-key
PUBMED_EMAIL=production-email@yourdomain.com

# Production Settings
ENVIRONMENT=production
LOG_LEVEL=WARNING
DEBUG=False
SECRET_KEY=your-secret-key-here

# Security
CORS_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
```

### Step 5: System Service Configuration

#### Create Systemd Service

```bash
sudo nano /etc/systemd/system/pake-system.service
```

**Service Configuration:**

```ini
[Unit]
Description=PAKE System API Server
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=pake
Group=pake
WorkingDirectory=/home/pake/pake-system
Environment=PATH=/home/pake/pake-system/venv/bin
ExecStart=/home/pake/pake-system/venv/bin/python mcp_server_standalone.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable pake-system
sudo systemctl start pake-system
sudo systemctl status pake-system
```

### Step 6: Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/pake-system
```

**Nginx Configuration:**

```nginx
server {
    listen 80;
    server_name yourdomain.com api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/pake/pake-system/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/pake-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 7: SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

## Docker Installation

### Using Docker Compose

```bash
# Clone repository
git clone https://github.com/pake-system/pake-system.git
cd pake-system

# Create environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Custom Docker Setup

```bash
# Build image
docker build -t pake-system:latest .

# Run container
docker run -d \
  --name pake-system \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379/0 \
  -e FIRECRAWL_API_KEY=your-key \
  pake-system:latest
```

## Configuration

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` | Yes |
| `FIRECRAWL_API_KEY` | Firecrawl API key | - | Yes |
| `PUBMED_EMAIL` | Email for PubMed API | - | Yes |
| `VAULT_PATH` | Path to Obsidian vault | - | No |
| `BRIDGE_PORT` | TypeScript bridge port | `3001` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `NEO4J_URI` | Neo4j connection URI | - | No |
| `NEO4J_USER` | Neo4j username | - | No |
| `NEO4J_PASSWORD` | Neo4j REDACTED_SECRET | - | No |
| `ENVIRONMENT` | Environment (development/production) | `development` | No |
| `DEBUG` | Debug mode | `True` | No |
| `SECRET_KEY` | Secret key for sessions | - | Yes (Production) |
| `CORS_ORIGINS` | Allowed CORS origins | `*` | No |
| `ALLOWED_HOSTS` | Allowed hosts | `*` | No |

### Configuration Files

#### Logging Configuration

```python
# config/logging.yaml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
  detailed:
    format: '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: logs/pake-system.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  pake_system:
    level: DEBUG
    handlers: [console, file]
    propagate: false
  
  uvicorn:
    level: INFO
    handlers: [console]
    propagate: false

root:
  level: INFO
  handlers: [console]
```

## Verification

### Health Checks

```bash
# API health check
curl http://localhost:8000/health

# Database connectivity
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://user:pass@localhost:5432/db')
print('Database connection: OK')
conn.close()
"

# Redis connectivity
python -c "
import redis
r = redis.Redis.from_url('redis://localhost:6379/0')
print('Redis connection:', r.ping())
"
```

### Functional Tests

```bash
# Test search functionality
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "test search", "max_results": 1}'

# Test ML dashboard
curl http://localhost:8000/ml/dashboard

# Test analytics
curl http://localhost:8000/analytics/system-health
```

### Performance Tests

```bash
# Run performance tests
python -m pytest tests/performance/ -v

# Load test (if available)
python scripts/load_test.py
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Error**: `psycopg2.OperationalError: connection refused`

**Solutions**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check if PostgreSQL is listening
sudo netstat -tlnp | grep 5432

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### 2. Redis Connection Errors

**Error**: `redis.exceptions.ConnectionError`

**Solutions**:
```bash
# Check Redis status
sudo systemctl status redis-server

# Check Redis configuration
redis-cli ping

# Restart Redis
sudo systemctl restart redis-server
```

#### 3. Port Already in Use

**Error**: `OSError: [Errno 98] Address already in use`

**Solutions**:
```bash
# Find process using port
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>

# Or change port in configuration
export PORT=8001
```

#### 4. Permission Errors

**Error**: `PermissionError: [Errno 13] Permission denied`

**Solutions**:
```bash
# Fix file permissions
sudo chown -R pake:pake /home/pake/pake-system
chmod +x scripts/*.py

# Check virtual environment
source venv/bin/activate
which python
```

#### 5. Missing Dependencies

**Error**: `ModuleNotFoundError: No module named 'xxx'`

**Solutions**:
```bash
# Reinstall dependencies
pip install -r requirements-phase7.txt

# Check Python version
python --version

# Recreate virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements-phase7.txt
```

### Log Analysis

```bash
# View application logs
tail -f logs/pake-system.log

# View system logs
sudo journalctl -u pake-system -f

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Performance Issues

#### High Memory Usage

```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Monitor system resources
htop
```

#### Slow Response Times

```bash
# Check database performance
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Check Redis performance
redis-cli info stats

# Monitor network
netstat -i
```

## Upgrading

### Backup Before Upgrade

```bash
# Backup database
pg_dump pake_system > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup configuration
cp .env .env.backup
cp -r config/ config.backup/
```

### Upgrade Process

```bash
# Stop services
sudo systemctl stop pake-system

# Backup current version
cp -r /home/pake/pake-system /home/pake/pake-system.backup

# Pull latest changes
cd /home/pake/pake-system
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements-phase7.txt

# Run database migrations
python scripts/migrate_database.py

# Start services
sudo systemctl start pake-system

# Verify upgrade
curl http://localhost:8000/health
```

### Rollback Process

```bash
# Stop services
sudo systemctl stop pake-system

# Restore previous version
rm -rf /home/pake/pake-system
mv /home/pake/pake-system.backup /home/pake/pake-system

# Restore database
sudo -u postgres psql pake_system < backup_YYYYMMDD_HHMMSS.sql

# Start services
sudo systemctl start pake-system
```

## Support

For installation support:

- **Documentation**: [https://docs.pake-system.com](https://docs.pake-system.com)
- **GitHub Issues**: [https://github.com/pake-system/issues](https://github.com/pake-system/issues)
- **Email**: support@pake-system.com
- **Discord**: [PAKE System Community](https://discord.gg/pake-system)

## Security Considerations

### Production Security Checklist

- [ ] Change default REDACTED_SECRETs
- [ ] Enable SSL/TLS
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Regular security updates
- [ ] Backup strategy implementation
- [ ] Access control configuration
- [ ] API rate limiting
- [ ] Input validation and sanitization
- [ ] Regular security audits

### Security Best Practices

1. **Use strong REDACTED_SECRETs** for all database and service accounts
2. **Enable SSL/TLS** for all communications
3. **Regular updates** of system packages and dependencies
4. **Monitor logs** for suspicious activity
5. **Implement backup** and disaster recovery procedures
6. **Use environment variables** for sensitive configuration
7. **Restrict network access** to necessary ports only
8. **Regular security audits** and penetration testing