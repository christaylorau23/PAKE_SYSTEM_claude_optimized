# 🆓 FREE Production Deployment with Environment Variables

## Overview

This guide provides **completely free** production deployment options using environment variables for secret management. No AWS costs, no premium services - just secure, environment-based configuration.

## 🏗️ Architecture

```
Development:
Application ──▶ .env file (local)

Production:
Application ──▶ Platform Environment Variables ──▶ Encrypted Storage
```

## 🆓 Free Platform Options

### **1. Railway (Recommended)**
- ✅ **$5/month free tier** (500 GB-hours)
- ✅ Built-in PostgreSQL & Redis
- ✅ Secure environment variable management
- ✅ Automatic HTTPS/SSL
- ✅ Git deployment

### **2. Render**
- ✅ **Free tier** for web services
- ✅ PostgreSQL available (paid add-on)
- ✅ Environment variable encryption
- ✅ Auto-deploy from Git

### **3. Fly.io**
- ✅ **Free allowance** (3 VMs, 160GB/month)
- ✅ Global deployment
- ✅ Built-in secrets management
- ✅ PostgreSQL & Redis add-ons

### **4. Self-hosted VPS**
- ✅ **$5-10/month** (DigitalOcean, Linode, Vultr)
- ✅ Full control over environment
- ✅ systemd environment files
- ✅ Docker environment variables

---

## 🚀 Platform-Specific Deployment

### **Railway Deployment**

#### Step 1: Prepare Repository
```bash
cd D:\Projects\PAKE_SYSTEM

# Validate environment configuration
python scripts/validate_production_env.py

# Create railway.json for configuration
cat > railway.json << 'EOF'
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python mcp-servers/base_server.py",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
EOF
```

#### Step 2: Deploy to Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and create project
railway login
railway new

# Add PostgreSQL database
railway add --database postgresql

# Add Redis cache  
railway add --database redis

# Set environment variables
railway variables set NODE_ENV=production

# Generate and set strong passwords
railway variables set DB_PASSWORD=$(python -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits+'!@#$%^&*') for _ in range(16)))")
railway variables set REDIS_PASSWORD=$(python -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits+'!@#$%^&*') for _ in range(16)))")

# Set API keys (replace with your actual keys)
railway variables set OPENAI_API_KEY=sk-your-actual-openai-key
railway variables set ANTHROPIC_API_KEY=sk-ant-your-actual-anthropic-key

# Deploy
railway up
```

#### Step 3: Configure Database Connection
```bash
# Railway automatically provides these variables:
# DATABASE_URL (PostgreSQL connection string)
# REDIS_URL (Redis connection string)

# The application will automatically detect and use these
```

### **Render Deployment**

#### Step 1: Create render.yaml
```yaml
# render.yaml
services:
  - type: web
    name: pake-system
    env: python
    buildCommand: "pip install -r mcp-servers/requirements.txt"
    startCommand: "python mcp-servers/base_server.py"
    envVars:
      - key: NODE_ENV
        value: production
      - key: DB_PASSWORD
        generateValue: true
        type: password
      - key: REDIS_PASSWORD  
        generateValue: true
        type: password
      - key: OPENAI_API_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false

databases:
  - name: pake-database
    databaseName: pake_system
    user: pake_user
```

#### Step 2: Deploy
```bash
# Connect your GitHub repository to Render
# Set environment variables in Render dashboard
# Deploy automatically from Git push
```

### **Fly.io Deployment**

#### Step 1: Create fly.toml
```toml
# fly.toml
app = "pake-system"
primary_region = "ord"

[build]
  builder = "paketobuildpacks/builder:base"
  buildpacks = ["gcr.io/paketo-buildpacks/python"]

[env]
  NODE_ENV = "production"
  PORT = "8080"

[[services]]
  http_checks = []
  internal_port = 8080
  processes = ["app"]
  protocol = "tcp"
  script_checks = []

  [services.concurrency]
    hard_limit = 25
    soft_limit = 20
    type = "connections"

  [[services.ports]]
    force_https = true
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

  [[services.tcp_checks]]
    grace_period = "1s"
    interval = "15s"
    restart_limit = 0
    timeout = "2s"
```

#### Step 2: Deploy to Fly.io
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and create app
fly auth login
fly apps create pake-system

# Add PostgreSQL
fly postgres create --name pake-postgres

# Add Redis
fly redis create --name pake-redis

# Set secrets
fly secrets set DB_PASSWORD=$(openssl rand -base64 24)
fly secrets set REDIS_PASSWORD=$(openssl rand -base64 16)
fly secrets set OPENAI_API_KEY=sk-your-actual-key
fly secrets set ANTHROPIC_API_KEY=sk-ant-your-actual-key

# Deploy
fly deploy
```

### **Self-hosted VPS Deployment**

#### Step 1: Server Setup (Ubuntu/Debian)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Python and dependencies
sudo apt install -y python3 python3-pip git nginx

# Clone repository
git clone https://github.com/yourusername/PAKE_SYSTEM.git
cd PAKE_SYSTEM
```

#### Step 2: Create Production Environment File
```bash
# Create secure environment file (NOT committed to git)
sudo mkdir -p /etc/pake-system
sudo chmod 700 /etc/pake-system

# Generate strong passwords
DB_PASSWORD=$(openssl rand -base64 24)
REDIS_PASSWORD=$(openssl rand -base64 16)

# Create environment file
sudo tee /etc/pake-system/production.env << EOF
# PAKE System Production Environment
NODE_ENV=production

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pake_system
DB_USER=pake_user
DB_PASSWORD=$DB_PASSWORD

# Redis Configuration  
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD

# API Keys (replace with actual values)
OPENAI_API_KEY=sk-your-actual-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-actual-anthropic-key-here
ELEVENLABS_API_KEY=your-actual-elevenlabs-key-here

# Application Configuration
BRIDGE_PORT=3000
MCP_SERVER_PORT=8000
LOG_LEVEL=INFO
EOF

# Secure the file
sudo chmod 600 /etc/pake-system/production.env
sudo chown root:root /etc/pake-system/production.env
```

#### Step 3: Create Docker Compose for Production
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: pake_system
      POSTGRES_USER: pake_user
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass_file /run/secrets/redis_password
    secrets:
      - redis_password
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped

  pake-system:
    build: .
    env_file:
      - /etc/pake-system/production.env
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs

secrets:
  db_password:
    external: true
  redis_password:
    external: true

volumes:
  postgres_data:
  redis_data:
```

#### Step 4: Create systemd Service
```bash
# Create systemd service file
sudo tee /etc/systemd/system/pake-system.service << 'EOF'
[Unit]
Description=PAKE System MCP Server
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=pake
Group=pake
WorkingDirectory=/opt/pake-system
EnvironmentFile=/etc/pake-system/production.env
ExecStart=/opt/pake-system/venv/bin/python mcp-servers/base_server.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/pake-system/logs

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable pake-system
sudo systemctl start pake-system
```

---

## 🔒 Security Best Practices

### **1. Strong Password Generation**
```bash
# Generate cryptographically secure passwords
python -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits+'!@#$%^&*') for _ in range(20)))"

# Or use openssl
openssl rand -base64 24
```

### **2. Environment Variable Validation**
```bash
# Run before each deployment
cd D:\Projects\PAKE_SYSTEM
python scripts/validate_production_env.py

# Expected output:
# ✅ Environment validation completed successfully!
# 🚀 Ready for production deployment
```

### **3. Environment Variable Encryption**

**Railway/Render/Fly.io:**
- Variables are automatically encrypted at rest
- Transmitted over HTTPS/TLS
- Access controlled by platform authentication

**Self-hosted:**
```bash
# Use systemd credential storage (Ubuntu 20.04+)
sudo systemd-creds encrypt --name=db_password - /etc/systemd/credentials/db_password.cred
sudo systemd-creds encrypt --name=redis_password - /etc/systemd/credentials/redis_password.cred

# Reference in systemd service
[Service]
LoadCredential=db_password:/etc/systemd/credentials/db_password.cred
LoadCredential=redis_password:/etc/systemd/credentials/redis_password.cred
Environment=DB_PASSWORD=%d/db_password
Environment=REDIS_PASSWORD=%d/redis_password
```

### **4. Access Control**
```bash
# Self-hosted: Limit SSH access
sudo ufw allow OpenSSH
sudo ufw enable

# Disable password authentication
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

### **5. Regular Security Updates**
```bash
# Create update script
tee ~/update-pake.sh << 'EOF'
#!/bin/bash
cd /opt/pake-system
git pull origin main
pip install -r requirements.txt
sudo systemctl restart pake-system
EOF

chmod +x ~/update-pake.sh

# Create cron job for weekly updates
echo "0 2 * * 0 /home/pake/update-pake.sh" | crontab -
```

---

## 📊 Cost Comparison

| Platform | Monthly Cost | Included | Best For |
|----------|-------------|----------|-----------|
| **Railway** | $5 | PostgreSQL, Redis, 500GB-hours | Quick deployment |
| **Render** | Free + $7 DB | Web service free, DB paid | Budget-conscious |
| **Fly.io** | Free tier | 3 VMs, 160GB/month | Global reach |
| **VPS** | $5-10 | Full server control | Maximum control |

## 🔧 Troubleshooting

### **Environment Variables Not Loading**
```bash
# Check if variables are set
env | grep -E "(DB_|REDIS_|NODE_ENV)"

# Test secret loading
python -c "
import os
import sys
sys.path.append('configs')
from secrets_manager import get_secret_manager
import asyncio

async def test():
    sm = get_secret_manager()
    print(f'Backend: {sm.backend.name}')
    config = await sm.get_database_config()
    print(f'DB Host: {config[\"host\"]}')
    print('Environment variables working!')

asyncio.run(test())
"
```

### **Database Connection Issues**
```bash
# Test database connectivity
python -c "
import asyncpg
import asyncio
import os

async def test_db():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'pake_system'),
            user=os.getenv('DB_USER', 'pake_user'),
            password=os.getenv('DB_PASSWORD')
        )
        await conn.execute('SELECT 1')
        print('Database connection successful!')
        await conn.close()
    except Exception as e:
        print(f'Database connection failed: {e}')

asyncio.run(test_db())
"
```

### **Application Won't Start**
```bash
# Check logs
tail -f logs/application.log

# For systemd service
sudo journalctl -u pake-system -f

# For Docker
docker-compose logs -f pake-system
```

---

## ✅ Deployment Checklist

### Pre-deployment
- [ ] **Secrets validated** with `validate_production_env.py`
- [ ] **Strong passwords** generated (16+ characters)
- [ ] **API keys** obtained and configured
- [ ] **.env** files excluded from git
- [ ] **Production branch** created and tested

### Platform Setup
- [ ] **Database** provisioned (PostgreSQL)
- [ ] **Cache** provisioned (Redis)
- [ ] **Environment variables** configured
- [ ] **Domain** configured (optional)
- [ ] **SSL/HTTPS** enabled

### Post-deployment
- [ ] **Health checks** passing (`/health` endpoint)
- [ ] **Database connectivity** verified
- [ ] **API endpoints** responding
- [ ] **Logs** showing successful startup
- [ ] **Monitoring** configured (optional)

---

## 🎉 Success!

Your PAKE System is now running in production with:

✅ **Zero AWS costs** - completely free secret management  
✅ **Enterprise security** - encrypted environment variables  
✅ **Platform flexibility** - works on any hosting provider  
✅ **Production validation** - automated environment checks  
✅ **Easy maintenance** - standard environment variable patterns  

**Total monthly cost: $0-10 depending on platform choice!**