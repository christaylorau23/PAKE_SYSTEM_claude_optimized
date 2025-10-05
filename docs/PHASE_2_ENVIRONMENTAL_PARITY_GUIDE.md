# PAKE System - Phase 2: Environmental Parity Debugging Guide

## Overview
This guide provides comprehensive instructions for using `act` to achieve environmental parity between local development and GitHub Actions CI/CD pipelines. The goal is to reliably reproduce CI failures locally for faster debugging.

## Prerequisites

### 1. Docker Installation
Ensure Docker is installed and running:
```bash
# Check Docker status
docker --version
docker info

# Start Docker if needed (Linux)
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. act Installation
Install act using the provided setup script:
```bash
# Run the setup script
./scripts/setup-phase2-act.sh

# Or install manually
# macOS
brew install act

# Linux
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Windows
choco install act-cli
# or
winget install --id=nektos.act
```

## Configuration Files

### 1. .actrc Configuration
The `.actrc` file contains act's default configuration:
```bash
# High-fidelity runner images
-P ubuntu-latest=catthehacker/ubuntu:full-22.04
-P ubuntu-20.04=catthehacker/ubuntu:full-20.04

# Container settings
--container-architecture linux/amd64
--bind
--artifact-server-path /tmp/act-artifacts

# Secret and variable files
--secret-file .secrets
--var-file .vars

# Debugging options
--verbose
```

### 2. .secrets File
Contains sensitive information needed for local testing:
```bash
# Required secrets
GITHUB_TOKEN=ghp_your_token_here
DATABASE_URL=postgresql://test_user:test_password@localhost:5432/pake_test
SECRET_KEY=test-secret-key-for-local-development

# External API keys
FIRECRAWL_API_KEY=your_firecrawl_api_key_here
ARXIV_API_KEY=your_arxiv_api_key_here
PUBMED_API_KEY=your_pubmed_api_key_here
```

### 3. .vars File
Contains non-sensitive configuration variables:
```bash
# Environment settings
ENVIRONMENT=local
DEBUG=true
LOG_LEVEL=debug

# Service URLs
API_BASE_URL=http://localhost:8000
BRIDGE_URL=http://localhost:3001

# Test configuration
TEST_TIMEOUT=300
COVERAGE_THRESHOLD=85
```

## Basic act Usage

### 1. List Available Jobs
```bash
# List all jobs in all workflows
act -l

# List jobs in a specific workflow
act -l -W .github/workflows/ci.yml

# List jobs with more details
act -l --verbose
```

### 2. Run Specific Jobs
```bash
# Run a single job
act -j lint-and-format

# Run multiple jobs
act -j lint-and-format -j static-analysis

# Run with specific workflow
act -W .github/workflows/ci.yml -j unit-tests
```

### 3. Simulate Different Events
```bash
# Simulate push event (default)
act push

# Simulate pull request event
act pull_request

# Simulate workflow dispatch
act workflow_dispatch
```

### 4. Advanced Options
```bash
# Dry run (see what would happen)
act --dry-run

# Use specific runner image
act -P ubuntu-latest=catthehacker/ubuntu:full-22.04

# Run with custom secrets
act --secret-file custom-secrets.env

# Run with custom variables
act --var-file custom-vars.env

# Run with specific platform
act --container-architecture linux/amd64
```

## Debugging Common Issues

### 1. Docker Permission Issues
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Restart Docker service
sudo systemctl restart docker
```

### 2. Runner Image Issues
```bash
# Pull runner images manually
docker pull catthehacker/ubuntu:full-22.04
docker pull catthehacker/ubuntu:full-20.04

# Use smaller images for testing
act -P ubuntu-latest=catthehacker/ubuntu:act-22.04
```

### 3. Secret/Variable Issues
```bash
# Check if files exist and are readable
ls -la .secrets .vars

# Validate file format
cat .secrets | grep -v "^#" | grep -v "^$"

# Test with minimal secrets
echo "GITHUB_TOKEN=test" > .secrets.test
act --secret-file .secrets.test -j lint-and-format
```

### 4. Network Issues
```bash
# Check Docker networking
docker network ls
docker network inspect bridge

# Use host networking (Linux)
act --bind --network host
```

### 5. Service Container Issues
```bash
# Start services manually for testing
docker run -d --name postgres-test \
  -e POSTGRES_USER=test_user \
  -e POSTGRES_PASSWORD=test_password \
  -e POSTGRES_DB=pake_test \
  -p 5432:5432 \
  postgres:16-alpine

docker run -d --name redis-test \
  -p 6379:6379 \
  redis:7-alpine

# Test service connectivity
docker exec postgres-test pg_isready
docker exec redis-test redis-cli ping
```

## Workflow-Specific Debugging

### 1. CI Pipeline (ci.yml)
```bash
# Test individual quality gates
act -j lint-and-format
act -j static-analysis
act -j security-scan
act -j unit-tests

# Test with services
act -j integration-tests
act -j e2e-tests
```

### 2. Comprehensive CI/CD (comprehensive-cicd.yml)
```bash
# Test build process
act -j build-and-scan

# Test deployment (requires secrets)
act -j deploy-staging
act -j deploy-production
```

### 3. Enhanced CI/CD (enhanced-cicd.yml)
```bash
# Test performance tests
act -j performance-tests

# Test with full test suite
act --var-file .vars --env run_full_test_suite=true -j performance-tests
```

## Performance Optimization

### 1. Image Caching
```bash
# Pre-pull commonly used images
docker pull catthehacker/ubuntu:full-22.04
docker pull postgres:16-alpine
docker pull redis:7-alpine

# Use smaller images for faster startup
act -P ubuntu-latest=catthehacker/ubuntu:act-22.04
```

### 2. Parallel Execution
```bash
# Run independent jobs in parallel
act -j lint-and-format &
act -j static-analysis &
wait
```

### 3. Selective Testing
```bash
# Test only changed components
act -j lint-and-format --path src/
act -j unit-tests --path tests/unit/
```

## Troubleshooting Checklist

### Before Running act
- [ ] Docker is running (`docker info`)
- [ ] act is installed (`act --version`)
- [ ] .secrets file exists and has required values
- [ ] .vars file exists and has required values
- [ ] .actrc file is configured correctly

### During Execution
- [ ] Check Docker logs (`docker logs <container>`)
- [ ] Monitor resource usage (`docker stats`)
- [ ] Verify network connectivity
- [ ] Check file permissions

### After Execution
- [ ] Review act output for errors
- [ ] Check generated artifacts
- [ ] Compare with GitHub Actions logs
- [ ] Document any differences

## Common Error Messages and Solutions

### "No space left on device"
```bash
# Clean up Docker resources
docker system prune -a
docker volume prune
```

### "Permission denied"
```bash
# Fix file permissions
chmod +x scripts/*.sh
chmod 600 .secrets
```

### "Container exited with code 1"
```bash
# Run with verbose output
act --verbose -j <job-name>

# Check container logs
docker logs <container-id>
```

### "Secret not found"
```bash
# Verify secrets file
cat .secrets | grep <secret-name>

# Check file permissions
ls -la .secrets
```

## Best Practices

### 1. Environment Isolation
- Use separate .secrets files for different environments
- Never commit secrets to version control
- Use .gitignore to exclude sensitive files

### 2. Incremental Testing
- Start with simple jobs (lint-and-format)
- Progress to complex jobs (integration-tests)
- Test one job at a time initially

### 3. Documentation
- Document any workflow-specific requirements
- Keep troubleshooting notes updated
- Share solutions with team members

### 4. Automation
- Create scripts for common act commands
- Use Makefile for complex workflows
- Integrate with IDE for easy access

## Integration with Development Workflow

### 1. Pre-commit Testing
```bash
# Test before pushing
act -j lint-and-format -j static-analysis

# Quick smoke test
act -j unit-tests --path tests/unit/smoke/
```

### 2. Debugging Failed CI
```bash
# Reproduce exact CI failure
act -j <failed-job-name> --verbose

# Compare with GitHub Actions
act -j <job-name> --env GITHUB_ACTIONS=true
```

### 3. Local Development
```bash
# Run full test suite locally
act

# Run specific test categories
act -j unit-tests -j integration-tests
```

## Advanced Features

### 1. Custom Runner Images
```bash
# Build custom runner with additional tools
docker build -t custom-runner -f Dockerfile.runner .

# Use custom runner
act -P ubuntu-latest=custom-runner
```

### 2. Artifact Handling
```bash
# Specify artifact server
act --artifact-server-path /tmp/act-artifacts

# Download artifacts from GitHub Actions
gh run download <run-id>
```

### 3. Matrix Strategy Testing
```bash
# Test specific matrix combinations
act -j unit-tests --matrix python-version:3.12,test-category:unit_functional
```

## Monitoring and Logging

### 1. Verbose Output
```bash
# Maximum verbosity
act --verbose --debug

# Log to file
act --verbose 2>&1 | tee act-debug.log
```

### 2. Resource Monitoring
```bash
# Monitor Docker resources
watch docker stats

# Check disk usage
df -h
docker system df
```

### 3. Performance Profiling
```bash
# Time job execution
time act -j <job-name>

# Profile with strace (Linux)
strace -f act -j <job-name>
```

This guide provides comprehensive coverage of using act for local GitHub Actions simulation. Follow the troubleshooting steps and best practices to achieve reliable environmental parity for faster CI debugging.
