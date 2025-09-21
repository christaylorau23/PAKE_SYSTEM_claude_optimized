# 🚀 PAKE System WSL Development Setup Guide

## 📋 First-Time WSL Setup Checklist

This guide will walk you through setting up the PAKE System in your WSL Ubuntu environment for the first time.

### 🎯 Quick Setup (Automated)

Run the automated setup script:

```bash
./setup-wsl-development.sh
```

This script will:
1. ✅ Create `.env` file with development settings
2. ✅ Install PostgreSQL and Redis
3. ✅ Set up database and user
4. ✅ Install Python and Node.js dependencies
5. ✅ Create required directories
6. ✅ Run database migrations

### 🔧 Manual Setup (Step by Step)

If you prefer to run each step manually:

#### 1. Configure Your Environment Variables (.env)

```bash
# Copy the production template to create your .env file
cp config/production.env .env

# Edit the .env file for development
nano .env
```

**Key settings to update in `.env`:**
- `FIRECRAWL_API_KEY=fc-your-development-firecrawl-api-key`
- `PUBMED_EMAIL=your-development-email@example.com`
- `DATABASE_URL=postgresql://pakeuser:password@localhost:5432/pake_db`
- `DEBUG=true`
- `DEVELOPMENT_MODE=true`

#### 2. Set Up PostgreSQL Database

```bash
# Update package list
sudo apt update

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo service postgresql start

# Enable PostgreSQL to start on boot
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql
```

In the PostgreSQL prompt:
```sql
CREATE DATABASE pake_db;
CREATE USER pakeuser WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE pake_db TO pakeuser;
ALTER USER pakeuser CREATEDB;
\q
```

#### 3. Install Redis

```bash
# Install Redis server
sudo apt install redis-server

# Start Redis service
sudo service redis-server start

# Enable Redis to start on boot
sudo systemctl enable redis-server
```

#### 4. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

#### 5. Set Up Node.js Environment

```bash
# Install NVM (if not already installed)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc

# Install Node.js 18
nvm install 18
nvm use 18

# Install dependencies
npm install
```

#### 6. Create Required Directories

```bash
mkdir -p logs vault backups vault-backups
```

#### 7. Run Database Migrations

```bash
# Activate virtual environment
source .venv/bin/activate

# Run Alembic migrations
alembic upgrade head
```

### 🚀 Starting the Servers

Once setup is complete, start the servers:

#### Terminal 1: Start the Bridge Server

```bash
# Switch to Node.js 18
nvm use 18

# Start the bridge server
yarn run start:bridge
```

#### Terminal 2: Start the Python Backend

```bash
# Activate Python virtual environment
source .venv/bin/activate

# Start the multi-tenant server
python mcp_server_multitenant.py
```

### 🔍 Health Checks

Verify everything is working:

```bash
# Check Bridge server
curl http://localhost:3001/health

# Check Python API
curl http://localhost:8000/docs

# Check database connection
psql -h localhost -U pakeuser -d pake_db -c "SELECT version();"

# Check Redis connection
redis-cli ping
```

### 🛠️ Development Commands

```bash
# Quick system health check
python scripts/test_production_pipeline.py

# API validation
python scripts/test_apis_simple.py

# Run tests
python -m pytest tests/ -v

# Development utilities
./dev-utils.sh health-check
```

### 📁 Project Structure

```
PAKE_SYSTEM_claude_optimized/
├── src/                    # Core source code
│   ├── services/           # Service implementations
│   ├── bridge/            # TypeScript Bridge v2.0
│   ├── api/               # API endpoints
│   └── utils/             # Shared utilities
├── config/                # Configuration files
├── tests/                 # Test suites
├── scripts/               # Utility scripts
├── docs/                  # Documentation
├── .env                   # Environment variables (created during setup)
├── requirements.txt       # Python dependencies
├── package.json           # Node.js dependencies
└── pyproject.toml         # Python project configuration
```

### 🔧 Troubleshooting

#### Common Issues:

1. **PostgreSQL connection refused**
   ```bash
   sudo service postgresql restart
   ```

2. **Redis connection refused**
   ```bash
   sudo service redis-server restart
   ```

3. **Python import errors**
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Node.js version issues**
   ```bash
   nvm use 18
   npm install
   ```

5. **Permission denied errors**
   ```bash
   chmod +x setup-wsl-development.sh
   ```

### 📚 Additional Resources

- **Main Documentation**: `README.md`
- **Development Guide**: `CLAUDE.md`
- **Project Structure**: `PROJECT_STRUCTURE.md`
- **Production Deployment**: `PRODUCTION_DEPLOYMENT_GUIDE.md`

### 🎉 Success Indicators

Your setup is complete when:
- ✅ Bridge server responds at `http://localhost:3001/health`
- ✅ Python API docs available at `http://localhost:8000/docs`
- ✅ Database migrations completed successfully
- ✅ All health checks pass
- ✅ CLI tool can connect to both MCP servers without "Disconnected" errors

---

**Need Help?** Check the troubleshooting section or refer to the comprehensive documentation in the `docs/` directory.
