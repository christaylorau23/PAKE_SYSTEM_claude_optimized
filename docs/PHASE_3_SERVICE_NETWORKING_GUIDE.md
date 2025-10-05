# Phase 3: Advanced CI Pipeline Interrogation

**Service Container Orchestration & Networking Mastery**

---

## Overview

Phase 3 addresses the **most complex CI-only failures** - those related to GitHub Actions platform-specific behaviors:
- Service container orchestration
- Network routing between job and services
- Health check timing
- Platform-specific file system behaviors

These issues are difficult to replicate locally and require deep understanding of GitHub Actions internals.

---

## The Critical Distinction: Two Networking Models

GitHub Actions uses **two completely different networking models** depending on how the job is configured:

### Model 1: Job Runs in Container

**Configuration**:
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    container: python:3.11-slim  # ← Job runs IN container
    services:
      postgres:
        image: postgres:14
```

**Networking**:
- ✅ Shared Docker bridge network
- ✅ Containers can resolve each other by service label
- ✅ Hostname = service label (e.g., `postgres`)
- ❌ Port mapping NOT required (and shouldn't be used)

**Connection String**:
```python
DATABASE_URL = "postgresql://user:pass@postgres:5432/db"
#                                      ^^^^^^^^
#                                      Service label, not localhost!
```

### Model 2: Job Runs on Host

**Configuration**:
```yaml
jobs:
  test:
    runs-on: ubuntu-latest  # ← Job runs ON host (no container key)
    services:
      postgres:
        image: postgres:14
        ports:
          - 5432:5432  # ← Port mapping REQUIRED
```

**Networking**:
- ✅ Services run in containers on separate network
- ✅ Job accesses via localhost with port mapping
- ✅ Hostname = `localhost` or `127.0.0.1`
- ✅ Port mapping REQUIRED

**Connection String**:
```python
DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
#                                      ^^^^^^^^^
#                                      localhost, not service label!
```

---

## Comparison Table

| Aspect | Container-Based Job | Host-Based Job |
|--------|---------------------|----------------|
| **Workflow Syntax** | `container: <image>` | `runs-on: ubuntu-latest` (no container key) |
| **Networking** | Shared Docker bridge | Host port mapping |
| **Service Hostname** | Service label (e.g., `postgres`) | `localhost` or `127.0.0.1` |
| **Port Mapping** | ❌ NOT required | ✅ REQUIRED |
| **Example DATABASE_URL** | `postgresql://user@postgres:5432/db` | `postgresql://user@localhost:5432/db` |
| **Common Use Case** | Consistent environment | Maximum flexibility |

---

## Your Current Configuration ✅

**Analysis Result**: All workflows follow best practices!

```bash
$ python3 scripts/validate_service_networking.py

✅ All service networking configurations are correct!

Configuration follows Phase 3 best practices:
  ✓ Correct networking model (host-based vs container-based)
  ✓ Proper port mappings
  ✓ Health checks configured
  ✓ Connection strings use correct hostnames
```

### What's Correct in Your Workflows

#### 1. **Networking Model**: Host-Based ✅

```yaml
jobs:
  integration-tests:
    runs-on: ubuntu-latest  # ← Host-based (no container key)
```

#### 2. **Port Mappings**: Correctly Configured ✅

```yaml
services:
  postgres:
    image: postgres:15
    ports:
      - 5432:5432  # ← Required for host-based

  redis:
    image: redis:7
    ports:
      - 6379:6379  # ← Required for host-based
```

#### 3. **Health Checks**: Properly Implemented ✅

```yaml
postgres:
  options: >-
    --health-cmd pg_isready
    --health-interval 10s
    --health-timeout 5s
    --health-retries 5

redis:
  options: >-
    --health-cmd "redis-cli ping"
    --health-interval 10s
    --health-timeout 5s
    --health-retries 5
```

#### 4. **Connection Strings**: Correct Hostnames ✅

```yaml
env:
  DATABASE_URL: postgresql://postgres:postgres@localhost:5432/pake_test
  #                                            ^^^^^^^^^
  #                                            Correct for host-based!
  REDIS_URL: redis://localhost:6379/0
  #                 ^^^^^^^^^
  #                 Correct for host-based!
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Wrong Hostname for Networking Model

**Symptom**: `Connection refused` errors in CI

**Cause**: Using `localhost` with container-based jobs or service label with host-based jobs

**Example (WRONG)**:
```yaml
# Host-based job
jobs:
  test:
    runs-on: ubuntu-latest  # Host-based
    services:
      postgres:
        image: postgres:14
        ports: ['5432:5432']
    steps:
      - run: pytest
        env:
          DATABASE_URL: postgresql://user@postgres:5432/db  # ← WRONG! Should be localhost
```

**Fix**:
```yaml
env:
  DATABASE_URL: postgresql://user@localhost:5432/db  # ← CORRECT
```

### Pitfall 2: Missing Port Mapping for Host-Based Jobs

**Symptom**: `Connection refused` even though service is running

**Cause**: Forgot port mapping in host-based job

**Example (WRONG)**:
```yaml
services:
  postgres:
    image: postgres:14
    # Missing ports!
```

**Fix**:
```yaml
services:
  postgres:
    image: postgres:14
    ports:
      - 5432:5432  # ← Add port mapping
```

### Pitfall 3: Missing or Incorrect Health Checks

**Symptom**: Intermittent test failures, race conditions

**Cause**: Tests start before service is ready

**Example (WRONG)**:
```yaml
services:
  postgres:
    image: postgres:14
    ports: ['5432:5432']
    # Missing health check!
```

**Fix**:
```yaml
services:
  postgres:
    image: postgres:14
    ports: ['5432:5432']
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

### Pitfall 4: Unnecessary Port Mapping in Container-Based Jobs

**Symptom**: Warning about unused port mappings

**Cause**: Using port mappings when job runs in container

**Example (SUBOPTIMAL)**:
```yaml
jobs:
  test:
    container: python:3.11  # Container-based
    services:
      postgres:
        image: postgres:14
        ports: ['5432:5432']  # ← Not needed for container-based!
```

**Fix**:
```yaml
jobs:
  test:
    container: python:3.11
    services:
      postgres:
        image: postgres:14
        # No ports needed - use service label 'postgres' directly
```

---

## Validation Tool Usage

### Basic Validation

```bash
# Validate all workflows
python3 scripts/validate_service_networking.py

# Validate specific workflow
python3 scripts/validate_service_networking.py --workflow .github/workflows/ci.yml
```

### Validation Output

**All Correct**:
```
✅ All service networking configurations are correct!

Configuration follows Phase 3 best practices:
  ✓ Correct networking model (host-based vs container-based)
  ✓ Proper port mappings
  ✓ Health checks configured
  ✓ Connection strings use correct hostnames
```

**Issues Found**:
```
❌ Found 2 error(s):

1. [ERROR] missing_port_mapping
   Job: integration-tests
   Service: postgres
   Problem: Service 'postgres' missing port mapping.
            Host-based jobs require explicit port mapping to access services.
   Fix: Add 'ports' to service 'postgres', e.g., ports: ['5432:5432']

2. [ERROR] incorrect_hostname
   Job: integration-tests
   Service: postgres
   Problem: DATABASE_URL uses 'postgres' but should use 'localhost'
            for host-based networking.
   Fix: Change DATABASE_URL to use '@localhost:'
```

---

## Health Check Reference

### PostgreSQL

```yaml
options: >-
  --health-cmd pg_isready
  --health-interval 10s
  --health-timeout 5s
  --health-retries 5
```

### Redis

```yaml
options: >-
  --health-cmd "redis-cli ping"
  --health-interval 10s
  --health-timeout 5s
  --health-retries 5
```

### MySQL / MariaDB

```yaml
options: >-
  --health-cmd "mysqladmin ping"
  --health-interval 10s
  --health-timeout 5s
  --health-retries 5
```

### MongoDB

```yaml
options: >-
  --health-cmd "mongosh --eval 'db.adminCommand({ping: 1})'"
  --health-interval 10s
  --health-timeout 5s
  --health-retries 5
```

### Elasticsearch

```yaml
options: >-
  --health-cmd "curl -f http://localhost:9200/_cluster/health"
  --health-interval 10s
  --health-timeout 5s
  --health-retries 5
```

---

## Debugging Service Connection Issues

### Step 1: Verify Service is Running

Add diagnostic step before tests:

```yaml
- name: Verify services are ready
  run: |
    echo "Checking PostgreSQL..."
    nc -zv localhost 5432

    echo "Checking Redis..."
    nc -zv localhost 6379

    echo "Testing PostgreSQL connection..."
    PGPASSWORD=postgres psql -h localhost -U postgres -d pake_test -c "SELECT version();"

    echo "Testing Redis connection..."
    redis-cli -h localhost ping
```

### Step 2: Check Service Logs

```yaml
- name: Show service logs
  if: failure()
  run: |
    docker logs $(docker ps -q --filter ancestor=postgres:15) || true
    docker logs $(docker ps -q --filter ancestor=redis:7) || true
```

### Step 3: Verify Network Connectivity

```yaml
- name: Debug network
  run: |
    echo "Running containers:"
    docker ps

    echo "Network inspection:"
    docker network ls
    docker network inspect bridge

    echo "Port mappings:"
    netstat -tlnp | grep -E '(5432|6379)'
```

---

## Integration with Debugging System

Phase 3 validation is integrated into the debugging workflow:

```bash
# Integrated local debug now includes Phase 3 validation
make -f Makefile.act debug-local JOB=integration-tests

# This automatically:
# 1. Validates service networking configuration
# 2. Runs job locally with act
# 3. Captures artifacts
# 4. Analyzes environment differences
# 5. Provides recommendations
```

---

## Best Practices

### 1. Always Use Health Checks

**Why**: Prevents race conditions where tests start before service is ready

**How**:
```yaml
services:
  postgres:
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

### 2. Match Networking Model to Use Case

**Container-Based**:
- ✅ When you need identical environment across local/CI
- ✅ When using specific language/framework versions
- ✅ When isolating dependencies

**Host-Based**:
- ✅ When you need maximum speed (no container overhead)
- ✅ When using GitHub-hosted runner tools
- ✅ When flexibility is more important than perfect parity

### 3. Validate Before Pushing

```bash
# Validate workflows before committing
python3 scripts/validate_service_networking.py

# Test locally with act
make -f Makefile.act debug-local JOB=integration-tests
```

### 4. Document Your Networking Model

Add comments to workflow:

```yaml
jobs:
  integration-tests:
    # Uses host-based networking model
    # Services accessible via localhost with port mapping
    runs-on: ubuntu-latest

    services:
      postgres:
        # Port mapping required for host-based model
        ports: ['5432:5432']
```

---

## Advanced Scenarios

### Using Custom Networks

```yaml
jobs:
  test:
    container:
      image: python:3.11
      options: --network my-network  # Custom network
```

### Service Container Options

```yaml
services:
  postgres:
    image: postgres:14
    env:
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --lc-collate=C --lc-ctype=C"
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --shm-size=256mb
      --tmpfs /var/lib/postgresql/data:rw
```

### Multiple Database Instances

```yaml
services:
  postgres-main:
    image: postgres:14
    ports: ['5432:5432']

  postgres-replica:
    image: postgres:14
    ports: ['5433:5432']  # Different host port
```

---

## Troubleshooting

### Issue: "Connection refused" errors

**Check**:
1. ✅ Port mapping exists (for host-based jobs)
2. ✅ Health check is passing
3. ✅ Correct hostname in connection string
4. ✅ Service started before tests

**Debug**:
```bash
# Run validation
python3 scripts/validate_service_networking.py

# Check logs
docker logs <container-id>
```

### Issue: Intermittent failures

**Likely Cause**: Race condition (tests start before service ready)

**Fix**: Add/improve health check

```yaml
options: >-
  --health-cmd pg_isready
  --health-interval 5s   # Check more frequently
  --health-timeout 3s
  --health-retries 10    # More retries
```

### Issue: Different behavior local vs CI

**Check**: Networking model mismatch

**Local (docker-compose)** often uses service labels
**CI (host-based)** uses localhost

**Fix**: Use environment variables to switch:

```python
import os
DB_HOST = os.getenv("DB_HOST", "localhost")  # localhost for CI
DATABASE_URL = f"postgresql://user@{DB_HOST}:5432/db"
```

---

## Summary

✅ **Your Configuration Status**: All workflows follow Phase 3 best practices

✅ **Networking Model**: Host-based (correct for your setup)

✅ **Port Mappings**: Properly configured

✅ **Health Checks**: Implemented correctly

✅ **Connection Strings**: Use correct hostnames

**Next Steps**:
1. Continue using validation tool before pushing changes
2. Reference this guide when adding new services
3. Use integrated debugging system for service-related issues

---

For more information:
- **Integrated Debugging**: `docs/INTEGRATED_DEBUGGING_GUIDE.md`
- **Phase 1**: `docs/CI_FORENSIC_ANALYSIS.md`
- **Phase 2**: `docs/PHASE_2_ENVIRONMENTAL_PARITY_GUIDE.md`
