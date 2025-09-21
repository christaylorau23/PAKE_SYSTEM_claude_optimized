# 🔧 PAKE System Manual Setup Steps

## ✅ Completed Steps

1. **Environment Variables**: `.env` file created successfully with development settings

## 🚀 Remaining Manual Steps

Since the automated script requires sudo privileges, please run these commands manually:

### Step 1: Install PostgreSQL

```bash
# Update package list
sudo apt update

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo service postgresql start

# Enable PostgreSQL to start on boot
sudo systemctl enable postgresql
```

### Step 2: Set Up Database

```bash
# Create database and user
sudo -u postgres psql
```

In the PostgreSQL prompt, run these commands:
```sql
CREATE DATABASE pake_db;
CREATE USER pakeuser WITH PASSWORD 'REDACTED_SECRET';
GRANT ALL PRIVILEGES ON DATABASE pake_db TO pakeuser;
ALTER USER pakeuser CREATEDB;
\q
```

### Step 3: Install Redis

```bash
# Install Redis server
sudo apt install redis-server

# Start Redis service
sudo service redis-server start

# Enable Redis to start on boot
sudo systemctl enable redis-server
```

### Step 4: Set Up Python Environment

```bash
# Activate virtual environment (if not already active)
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 5: Set Up Node.js Environment

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

### Step 6: Create Required Directories

```bash
mkdir -p logs vault backups vault-backups
```

### Step 7: Run Database Migrations

```bash
# Activate virtual environment
source .venv/bin/activate

# Run Alembic migrations
alembic upgrade head
```

## 🎯 Starting the Servers

Once all steps are complete:

### Terminal 1: Start Bridge Server

```bash
nvm use 18
yarn run start:bridge
```

### Terminal 2: Start Python Backend

```bash
source .venv/bin/activate
python mcp_server_multitenant.py
```

## 🔍 Health Checks

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

## ⚠️ Important Notes

1. **Update API Keys**: Edit `.env` file and update:
   - `FIRECRAWL_API_KEY=fc-your-development-firecrawl-api-key`
   - `PUBMED_EMAIL=your-development-email@example.com`

2. **Virtual Environment**: Always activate the Python virtual environment:
   ```bash
   source .venv/bin/activate
   ```

3. **Node.js Version**: Use Node.js 18 for the bridge:
   ```bash
   nvm use 18
   ```

## 🆘 Troubleshooting

If you encounter issues:

1. **Permission denied**: Make sure you're not running as root
2. **Service not starting**: Check with `sudo systemctl status postgresql` or `sudo systemctl status redis-server`
3. **Import errors**: Ensure virtual environment is activated and dependencies are installed
4. **Port conflicts**: Check if ports 3001 and 8000 are available

## 📞 Need Help?

Run the health check script:
```bash
./dev-utils.sh health-check
```

Or check the comprehensive documentation in `WSL_SETUP_GUIDE.md`.
