# Environment Setup Guide - Python 3.12.8 Consistency

This guide ensures your local development environment matches the CI/CD requirements exactly, preventing "works on my machine" issues.

## 🎯 Required Versions

| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | `3.12.8` | Core backend runtime |
| **Poetry** | `1.8.3` | Python dependency management |
| **Node.js** | `22.18.0` | TypeScript bridge runtime |
| **Docker** | Latest | Containerization |

## 🔧 Automated Setup

### Quick Setup Script

Run the automated environment setup:

```bash
# Make script executable and run
chmod +x scripts/setup_environment.sh
./scripts/setup_environment.sh
```

This script will:
- ✅ Check Python 3.12.8 installation
- ✅ Validate Poetry 1.8.3 installation
- ✅ Verify Node.js 22.18.0 installation
- ✅ Install all dependencies
- ✅ Run environment validation

### Environment Validation

Validate your environment matches CI requirements:

```bash
python3 scripts/validate_environment.py
```

## 🐍 Python Version Management

### Using pyenv (Recommended)

1. **Install pyenv:**
   ```bash
   curl https://pyenv.run | bash

   # Add to your shell profile (~/.bashrc or ~/.zshrc)
   export PATH="$HOME/.pyenv/bin:$PATH"
   eval "$(pyenv init -)"
   ```

2. **Install Python 3.12.8:**
   ```bash
   pyenv install 3.12.8
   pyenv local 3.12.8
   ```

3. **Verify installation:**
   ```bash
   python --version  # Should output: Python 3.12.8
   ```

### Alternative: System Python

If using system Python, ensure version 3.12.8 is installed:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev

# macOS (using Homebrew)
brew install python@3.12

# Verify
python3.12 --version
```

## 📦 Poetry Installation

Install Poetry for dependency management:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Add Poetry to your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Verify installation:
```bash
poetry --version  # Should output: Poetry (version 1.8.3)
```

## 🟢 Node.js Installation

### Using nvm (Recommended)

1. **Install nvm:**
   ```bash
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   ```

2. **Install Node.js 22.18.0:**
   ```bash
   nvm install 22.18.0
   nvm use 22.18.0
   nvm alias default 22.18.0
   ```

3. **Verify installation:**
   ```bash
   node --version  # Should output: v22.18.0
   ```

## 🚀 Project Setup

### 1. Clone and Setup Python Environment

```bash
# Clone repository
git clone <repository-url>
cd PAKE_SYSTEM_claude_optimized

# Install Python dependencies
poetry install

# Activate virtual environment
poetry shell
```

### 2. Setup TypeScript Bridge

```bash
# Navigate to bridge directory
cd src/bridge

# Install Node.js dependencies
npm ci

# Build TypeScript
npm run build
```

### 3. Environment Configuration

Create environment file:
```bash
cp env.example .env
```

Edit `.env` with your configuration:
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/pake_db

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys (get from respective services)
FIRECRAWL_API_KEY=your_firecrawl_key
ARXIV_API_KEY=your_arxiv_key
PUBMED_API_KEY=your_pubmed_key
```

## 🐳 Docker Environment

### Build Production Images

```bash
# Build Python backend
docker build -f Dockerfile.production -t pake-system:latest .

# Build TypeScript bridge
docker build -f Dockerfile.bridge.production -t pake-bridge:latest .
```

### Development with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## ✅ Validation Checklist

Before starting development, ensure:

- [ ] Python 3.12.8 installed and active
- [ ] Poetry 1.8.3 installed
- [ ] Node.js 22.18.0 installed
- [ ] `.python-version` file exists with `3.12.8`
- [ ] `poetry.lock` file is up to date
- [ ] All dependencies installed (`poetry install`)
- [ ] TypeScript bridge built (`npm run build`)
- [ ] Environment variables configured
- [ ] Docker images build successfully
- [ ] Tests pass (`poetry run pytest`)

## 🔍 Troubleshooting

### Python Version Issues

**Problem:** Wrong Python version
```bash
# Check current version
python --version

# Switch to correct version (pyenv)
pyenv local 3.12.8

# Verify
python --version
```

**Problem:** Poetry not found
```bash
# Reinstall Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

### Dependency Issues

**Problem:** Poetry lock file outdated
```bash
# Update lock file
poetry lock

# Reinstall dependencies
poetry install
```

**Problem:** Node.js version mismatch
```bash
# Switch to correct version (nvm)
nvm use 22.18.0

# Reinstall dependencies
npm ci
```

### Docker Issues

**Problem:** Docker build fails
```bash
# Clean Docker cache
docker system prune -a

# Rebuild images
docker build --no-cache -f Dockerfile.production -t pake-system:latest .
```

## 📋 CI/CD Alignment

The CI pipeline uses these exact versions:

```yaml
# .github/workflows/ci.yml
env:
  PYTHON_VERSION: '3.12'
  POETRY_VERSION: '1.8.3'
  NODE_VERSION: '22.18.0'
```

Your local environment should match these versions exactly to prevent CI failures.

## 🎯 Next Steps

After successful environment setup:

1. **Run Tests:** `poetry run pytest`
2. **Start Development Server:** `poetry run python mcp_server_standalone.py`
3. **Start TypeScript Bridge:** `cd src/bridge && npm start`
4. **Access Dashboard:** Open `http://localhost:3000`

## 📚 Additional Resources

- [Python 3.12 Documentation](https://docs.python.org/3.12/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [Node.js 22 Documentation](https://nodejs.org/docs/latest-v22.x/)
- [Docker Documentation](https://docs.docker.com/)

---

**Need Help?** Run `./scripts/setup_environment.sh` for automated setup or `python3 scripts/validate_environment.py` for environment validation.
