# 🚀 PAKE System - Final Setup Commands

## 📋 Your First-Time WSL Setup Checklist

### ✅ COMPLETED STEPS
1. **Environment Variables**: `.env` file created with development settings
2. **Python Environment**: Virtual environment ready with Python 3.10.4
3. **Node.js Environment**: Node.js v22.19.0 and npm v10.9.3 installed
4. **PostgreSQL**: Service installed and running

### 🔧 REMAINING MANUAL STEPS

#### Step 1: Configure PostgreSQL Database
```bash
# Create database and user
sudo -u postgres psql
```

In the PostgreSQL prompt:
```sql
CREATE DATABASE pake_db;
CREATE USER pakeuser WITH PASSWORD 'REDACTED_SECRET';
GRANT ALL PRIVILEGES ON DATABASE pake_db TO pakeuser;
ALTER USER pakeuser CREATEDB;
\q
```

#### Step 2: Install Redis
```bash
# Install Redis server
sudo apt install redis-server

# Start Redis service
sudo service redis-server start

# Enable Redis to start on boot
sudo systemctl enable redis-server
```

#### Step 3: Update API Keys (IMPORTANT!)
Edit the `.env` file and update these values:
```bash
nano .env
```

Update these lines:
```
FIRECRAWL_API_KEY=fc-your-actual-firecrawl-api-key
PUBMED_EMAIL=your-actual-email@example.com
```

#### Step 4: Run Database Migrations
```bash
# Activate virtual environment
source .venv/bin/activate

# Run Alembic migrations
alembic upgrade head
```

#### Step 5: Install Node.js Dependencies
```bash
# Install all dependencies
npm install
```

## 🚀 Starting the Servers

### Terminal 1: Start the Bridge Server
```bash
cd /home/chris/projects/PAKE_SYSTEM_claude_optimized
npm run start:bridge
```

### Terminal 2: Start the Python Backend
```bash
cd /home/chris/projects/PAKE_SYSTEM_claude_optimized
source .venv/bin/activate
python mcp_server_multitenant.py
```

## 🔍 Health Checks

After starting both servers, verify everything is working:

```bash
# Check Bridge server (should return health status)
curl http://localhost:3001/health

# Check Python API (should open API documentation)
curl http://localhost:8000/docs

# Check database connection
psql -h localhost -U pakeuser -d pake_db -c "SELECT version();"

# Check Redis connection
redis-cli ping
```

## 🎯 Available Server Options

You have several server options available:

1. **`mcp_server_multitenant.py`** - Enterprise multi-tenant server (RECOMMENDED)
2. **`mcp_server_realtime.py`** - Real-time features with WebSocket support
3. **`mcp_server_auth.py`** - Authentication-enabled server
4. **`mcp_server_database.py`** - Database-persistent server
5. **`mcp_server_standalone.py`** - Standalone server
6. **`mcp_server.py`** - Basic server

## 🛠️ Development Commands

```bash
# Quick system health check
python scripts/test_production_pipeline.py

# API validation
python scripts/test_apis_simple.py

# Run all tests
npm run test

# Development utilities
./dev-utils.sh health-check
```

## 📊 Expected Results

When everything is working correctly:

- **Bridge Server**: `http://localhost:3001/health` returns health status
- **Python API**: `http://localhost:8000/docs` shows API documentation
- **Database**: Connection successful with `pake_db` database
- **Redis**: `PONG` response from `redis-cli ping`
- **CLI Tool**: Can connect to both MCP servers without "Disconnected" errors

## 🆘 Troubleshooting

### PostgreSQL Issues
```bash
# Check service status
sudo systemctl status postgresql

# Restart if needed
sudo service postgresql restart
```

### Redis Issues
```bash
# Check service status
sudo systemctl status redis-server

# Test connection
redis-cli ping
```

### Port Conflicts
```bash
# Check what's using ports 3001 and 8000
netstat -tulpn | grep :3001
netstat -tulpn | grep :8000
```

### Python Environment Issues
```bash
# Reactivate virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Node.js Issues
```bash
# Install dependencies
npm install

# Check Node.js version
node --version
```

## 🎉 Success Indicators

Your setup is complete when:
- ✅ Both servers start without errors
- ✅ Health checks return successful responses
- ✅ Database and Redis connections work
- ✅ CLI tool connects to MCP servers successfully
- ✅ No "Disconnected" errors in your CLI tool

---

**Ready to proceed?** Run the remaining setup steps above, then start both servers!
