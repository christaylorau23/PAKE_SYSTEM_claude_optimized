# PAKE System - Enterprise Deployment Guide

**Version**: 10.2.0  
**Last Updated**: September 14, 2025  
**Status**: Production Ready  

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Pre-deployment Checklist](#pre-deployment-checklist)
4. [Installation Methods](#installation-methods)
5. [Configuration](#configuration)
6. [Security Hardening](#security-hardening)
7. [Production Deployment](#production-deployment)
8. [Monitoring & Maintenance](#monitoring--maintenance)
9. [Troubleshooting](#troubleshooting)
10. [Backup & Recovery](#backup--recovery)

---

## 🎯 Overview

The PAKE System is an enterprise-grade knowledge management platform with multi-source ingestion, AI intelligence, advanced analytics, and enhanced Obsidian integration. This guide provides comprehensive instructions for deploying the system in production environments.

### Key Features
- **Multi-source Research**: Web, ArXiv, PubMed integration
- **AI Intelligence**: Semantic search, auto-tagging, metadata extraction
- **Advanced Analytics**: Real-time insights, anomaly detection, predictive analytics
- **Enhanced Obsidian Integration**: Bidirectional sync, knowledge graph
- **Enterprise Security**: JWT authentication, comprehensive audit logging
- **High Performance**: Sub-second response times, enterprise caching

---

## 🖥️ System Requirements

### Minimum Requirements
- **CPU**: 4 cores, 2.4 GHz
- **RAM**: 8 GB
- **Storage**: 50 GB SSD
- **OS**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **Network**: 100 Mbps connection

### Recommended Production Requirements
- **CPU**: 8+ cores, 3.0+ GHz
- **RAM**: 32+ GB
- **Storage**: 500+ GB NVMe SSD
- **OS**: Ubuntu 22.04 LTS / RHEL 9
- **Network**: 1+ Gbps connection
- **Load Balancer**: HAProxy / Nginx
- **Database**: PostgreSQL 14+
- **Cache**: Redis 6+

### Software Dependencies
- **Python**: 3.12+
- **Node.js**: 22.18.0+
- **PostgreSQL**: 14+
- **Redis**: 6+
- **Docker**: 20.10+ (optional)
- **Kubernetes**: 1.24+ (optional)

---

## ✅ Pre-deployment Checklist

### Security Checklist
- [ ] SSL certificates obtained and configured
- [ ] Firewall rules configured
- [ ] Security audit completed
- [ ] Environment variables secured
- [ ] API keys rotated and secured
- [ ] Database credentials secured
- [ ] Backup encryption configured

### Infrastructure Checklist
- [ ] Server provisioning completed
- [ ] Domain name configured
- [ ] DNS records set up
- [ ] Load balancer configured
- [ ] Database server provisioned
- [ ] Redis server provisioned
- [ ] Monitoring tools installed
- [ ] Log aggregation configured

### Application Checklist
- [ ] Code repository cloned
- [ ] Dependencies installed
- [ ] Configuration files created
- [ ] Database migrations run
- [ ] Initial data loaded
- [ ] Health checks passing
- [ ] Performance benchmarks met

---

## 🚀 Installation Methods

### Method 1: Manual Installation

#### Step 1: Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.12 python3.12-venv python3-pip nodejs npm postgresql redis-server nginx

# Create application user
sudo useradd -m -s /bin/bash pake
sudo usermod -aG sudo pake
```

#### Step 2: Application Installation
```bash
# Switch to application user
sudo su - pake

# Clone repository
git clone https://github.com/your-org/pake-system.git
cd pake-system

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements-phase7.txt

# Install Node.js dependencies
cd src/bridge
npm install
cd ../..

# Set up database
sudo -u postgres createdb pake_system
sudo -u postgres createuser pake_user
sudo -u postgres psql -c "ALTER USER pake_user PASSWORD 'secure_REDACTED_SECRET';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE pake_system TO pake_user;"
```

#### Step 3: Configuration
```bash
# Create environment file
cp .env.example .env.production

# Edit configuration
nano .env.production
```

### Method 2: Docker Deployment

#### Docker Compose Setup
```yaml
# docker-compose.yml
version: '3.8'

services:
  pake-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://pake_user:REDACTED_SECRET@postgres:5432/pake_system
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ./vault:/app/vault
    restart: unless-stopped

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=pake_system
      - POSTGRES_USER=pake_user
      - POSTGRES_PASSWORD=secure_REDACTED_SECRET
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - pake-api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

#### Deployment Commands
```bash
# Build and start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f pake-api
```

### Method 3: Kubernetes Deployment

#### Namespace and ConfigMap
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: pake-system

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pake-config
  namespace: pake-system
data:
  DATABASE_URL: "postgresql://pake_user:REDACTED_SECRET@postgres-service:5432/pake_system"
  REDIS_URL: "redis://redis-service:6379"
  VAULT_PATH: "/app/vault"
```

#### Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pake-api
  namespace: pake-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pake-api
  template:
    metadata:
      labels:
        app: pake-api
    spec:
      containers:
      - name: pake-api
        image: pake-system:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: pake-config
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

## ⚙️ Configuration

### Environment Variables

#### Core Configuration
```bash
# Application Settings
APP_NAME="PAKE System"
APP_VERSION="10.2.0"
APP_ENV="production"
DEBUG=false
LOG_LEVEL="INFO"

# Server Configuration
HOST="0.0.0.0"
PORT=8000
WORKERS=4

# Database Configuration
DATABASE_URL="postgresql://pake_user:REDACTED_SECRET@localhost:5432/pake_system"
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis Configuration
REDIS_URL="redis://localhost:6379"
REDIS_PASSWORD=""
REDIS_DB=0

# Security Configuration
SECRET_KEY="your-super-secret-key-here"
JWT_SECRET_KEY="your-jwt-secret-key-here"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# API Keys
FIRECRAWL_API_KEY="your-firecrawl-api-key"
PUBMED_EMAIL="your-email@domain.com"

# Obsidian Integration
VAULT_PATH="/path/to/obsidian/vault"
BRIDGE_PORT=3001
AUTO_TAG_ENABLED=true
KNOWLEDGE_GRAPH_ENABLED=true
```

#### Security Configuration
```bash
# CORS Settings
ALLOWED_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
ALLOWED_METHODS="GET,POST,PUT,DELETE,OPTIONS"
ALLOWED_HEADERS="*"

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# SSL/TLS
SSL_CERT_PATH="/path/to/cert.pem"
SSL_KEY_PATH="/path/to/key.pem"
FORCE_HTTPS=true
```

### Nginx Configuration

#### Production Nginx Config
```nginx
# /etc/nginx/sites-available/pake-system
upstream pake_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://pake_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /static/ {
        alias /path/to/static/files/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Systemd Service Configuration

#### PAKE API Service
```ini
# /etc/systemd/system/pake-api.service
[Unit]
Description=PAKE System API
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=exec
User=pake
Group=pake
WorkingDirectory=/home/pake/pake-system
Environment=PATH=/home/pake/pake-system/venv/bin
ExecStart=/home/pake/pake-system/venv/bin/python mcp_server_standalone.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/pake/pake-system

[Install]
WantedBy=multi-user.target
```

#### Obsidian Bridge Service
```ini
# /etc/systemd/system/pake-bridge.service
[Unit]
Description=PAKE Obsidian Bridge
After=network.target pake-api.service
Requires=pake-api.service

[Service]
Type=exec
User=pake
Group=pake
WorkingDirectory=/home/pake/pake-system/src/bridge
Environment=NODE_PATH=/usr/local/lib/node_modules
Environment=VAULT_PATH=/home/pake/pake-system/vault
Environment=BRIDGE_PORT=3001
ExecStart=/usr/bin/node obsidian_bridge.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 🔒 Security Hardening

### SSL/TLS Configuration
```bash
# Generate SSL certificate (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com

# Or use custom certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/pake.key \
  -out /etc/ssl/certs/pake.crt
```

### Firewall Configuration
```bash
# UFW Configuration
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8000/tcp  # Block direct API access
sudo ufw deny 3001/tcp  # Block direct bridge access
```

### Database Security
```sql
-- PostgreSQL security configuration
-- /etc/postgresql/14/main/postgresql.conf
ssl = on
ssl_cert_file = '/etc/ssl/certs/server.crt'
ssl_key_file = '/etc/ssl/private/server.key'

-- Create restricted user
CREATE USER pake_readonly WITH PASSWORD 'readonly_REDACTED_SECRET';
GRANT CONNECT ON DATABASE pake_system TO pake_readonly;
GRANT USAGE ON SCHEMA public TO pake_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO pake_readonly;
```

### Application Security
```bash
# Set secure file permissions
chmod 600 .env.production
chmod 700 /home/pake/pake-system
chown -R pake:pake /home/pake/pake-system

# Disable unnecessary services
sudo systemctl disable apache2
sudo systemctl disable mysql
```

---

## 🚀 Production Deployment

### Deployment Script
```bash
#!/bin/bash
# deploy.sh - Production deployment script

set -e

echo "Starting PAKE System deployment..."

# Backup current deployment
if [ -d "/home/pake/pake-system" ]; then
    echo "Creating backup..."
    sudo cp -r /home/pake/pake-system /home/pake/pake-system.backup.$(date +%Y%m%d_%H%M%S)
fi

# Pull latest code
cd /home/pake/pake-system
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements-phase7.txt

# Run database migrations
python -c "from src.services.database.migrations import run_migrations; run_migrations()"

# Restart services
sudo systemctl restart pake-api
sudo systemctl restart pake-bridge
sudo systemctl reload nginx

# Health check
sleep 10
curl -f http://localhost:8000/health || exit 1

echo "Deployment completed successfully!"
```

### Health Check Script
```bash
#!/bin/bash
# health_check.sh - Comprehensive health check

BASE_URL="http://localhost:8000"
BRIDGE_URL="http://localhost:3001"

echo "Running health checks..."

# API Health
echo "Checking API health..."
curl -f "$BASE_URL/health" || exit 1

# Bridge Health
echo "Checking bridge health..."
curl -f "$BRIDGE_URL/health" || exit 1

# Database connectivity
echo "Checking database..."
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://pake_user:REDACTED_SECRET@localhost:5432/pake_system')
conn.close()
print('Database OK')
" || exit 1

# Redis connectivity
echo "Checking Redis..."
python -c "
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.ping()
print('Redis OK')
" || exit 1

echo "All health checks passed!"
```

---

## 📊 Monitoring & Maintenance

### Monitoring Setup

#### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'pake-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'pake-bridge'
    static_configs:
      - targets: ['localhost:3001']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

#### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "PAKE System Monitoring",
    "panels": [
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      }
    ]
  }
}
```

### Log Management

#### Logrotate Configuration
```bash
# /etc/logrotate.d/pake-system
/home/pake/pake-system/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 pake pake
    postrotate
        systemctl reload pake-api
    endscript
}
```

#### ELK Stack Integration
```yaml
# logstash.conf
input {
  file {
    path => "/home/pake/pake-system/logs/*.log"
    type => "pake-logs"
  }
}

filter {
  if [type] == "pake-logs" {
    grok {
      match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{GREEDYDATA:message}" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "pake-logs-%{+YYYY.MM.dd}"
  }
}
```

### Maintenance Tasks

#### Automated Backup Script
```bash
#!/bin/bash
# backup.sh - Automated backup script

BACKUP_DIR="/backups/pake-system"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR/$DATE"

# Database backup
pg_dump -h localhost -U pake_user pake_system > "$BACKUP_DIR/$DATE/database.sql"

# Application files backup
tar -czf "$BACKUP_DIR/$DATE/application.tar.gz" /home/pake/pake-system

# Redis backup
redis-cli --rdb "$BACKUP_DIR/$DATE/redis.rdb"

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR/$DATE"
```

#### Performance Monitoring Script
```bash
#!/bin/bash
# performance_monitor.sh

LOG_FILE="/home/pake/pake-system/logs/performance.log"

while true; do
    # API response time
    RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health)
    
    # System metrics
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    DISK_USAGE=$(df -h / | awk 'NR==2{print $5}' | cut -d'%' -f1)
    
    # Log metrics
    echo "$(date): API_RESPONSE_TIME=${RESPONSE_TIME}s CPU=${CPU_USAGE}% MEMORY=${MEMORY_USAGE}% DISK=${DISK_USAGE}%" >> "$LOG_FILE"
    
    sleep 60
done
```

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: API Not Starting
```bash
# Check logs
journalctl -u pake-api -f

# Check port availability
netstat -tlnp | grep 8000

# Check dependencies
systemctl status postgresql redis
```

#### Issue: Database Connection Failed
```bash
# Test database connection
psql -h localhost -U pake_user -d pake_system

# Check PostgreSQL status
sudo systemctl status postgresql

# Check database permissions
sudo -u postgres psql -c "\du pake_user"
```

#### Issue: High Memory Usage
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Check for memory leaks
python -c "
import psutil
import gc
print('Memory before GC:', psutil.Process().memory_info().rss / 1024 / 1024, 'MB')
gc.collect()
print('Memory after GC:', psutil.Process().memory_info().rss / 1024 / 1024, 'MB')
"
```

#### Issue: Slow Response Times
```bash
# Check system load
uptime
top

# Check database performance
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Check Redis performance
redis-cli --latency-history
```

### Performance Optimization

#### Database Optimization
```sql
-- Create indexes for better performance
CREATE INDEX CONCURRENTLY idx_search_results_created_at ON search_results(created_at);
CREATE INDEX CONCURRENTLY idx_search_results_query ON search_results(query);
CREATE INDEX CONCURRENTLY idx_analytics_timestamp ON analytics_data(timestamp);

-- Analyze tables
ANALYZE search_results;
ANALYZE analytics_data;
```

#### Redis Optimization
```bash
# Redis configuration optimization
# /etc/redis/redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

---

## 💾 Backup & Recovery

### Backup Strategy

#### Full System Backup
```bash
#!/bin/bash
# full_backup.sh

BACKUP_DIR="/backups/full"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR/$DATE"

# Stop services
sudo systemctl stop pake-api pake-bridge

# Database backup
pg_dump -h localhost -U pake_user pake_system > "$BACKUP_DIR/$DATE/database.sql"

# Application backup
tar -czf "$BACKUP_DIR/$DATE/application.tar.gz" /home/pake/pake-system

# Configuration backup
tar -czf "$BACKUP_DIR/$DATE/config.tar.gz" /etc/nginx /etc/systemd/system/pake-*

# Redis backup
redis-cli --rdb "$BACKUP_DIR/$DATE/redis.rdb"

# Restart services
sudo systemctl start pake-api pake-bridge

echo "Full backup completed: $BACKUP_DIR/$DATE"
```

### Recovery Procedures

#### Database Recovery
```bash
# Restore database from backup
sudo systemctl stop pake-api
sudo -u postgres dropdb pake_system
sudo -u postgres createdb pake_system
psql -h localhost -U pake_user -d pake_system < /backups/database.sql
sudo systemctl start pake-api
```

#### Application Recovery
```bash
# Restore application files
sudo systemctl stop pake-api pake-bridge
rm -rf /home/pake/pake-system
tar -xzf /backups/application.tar.gz -C /
sudo systemctl start pake-api pake-bridge
```

### Disaster Recovery Plan

#### Recovery Checklist
1. [ ] Assess damage and determine recovery scope
2. [ ] Restore from most recent backup
3. [ ] Verify database integrity
4. [ ] Test application functionality
5. [ ] Update DNS if needed
6. [ ] Notify users of service restoration
7. [ ] Document incident and lessons learned

#### Recovery Time Objectives
- **RTO (Recovery Time Objective)**: 4 hours
- **RPO (Recovery Point Objective)**: 1 hour
- **Backup Frequency**: Daily full, hourly incremental
- **Backup Retention**: 30 days full, 7 days incremental

---

## 📞 Support & Resources

### Documentation
- [API Documentation](http://localhost:8000/docs)
- [OpenAPI Specification](docs/openapi.yaml)
- [User Manual](docs/USER_MANUAL.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)

### Monitoring Dashboards
- [System Health](http://localhost:8000/dashboard/realtime)
- [Advanced Analytics](http://localhost:8000/dashboard/advanced)
- [Obsidian Integration](http://localhost:8000/dashboard/obsidian)

### Support Contacts
- **Technical Support**: support@pake-system.com
- **Security Issues**: security@pake-system.com
- **Emergency**: +1-XXX-XXX-XXXX

---

**🎉 PAKE System Enterprise Deployment Guide Complete**

This guide provides comprehensive instructions for deploying the PAKE System in production environments. Follow the procedures carefully and maintain regular backups and monitoring for optimal system performance and reliability.
