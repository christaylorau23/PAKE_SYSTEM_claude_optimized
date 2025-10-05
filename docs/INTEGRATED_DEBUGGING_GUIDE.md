# 🔬 Integrated CI/CD Debugging Guide

**Complete workflow debugging solution combining forensic analysis + local simulation**

---

## 📋 Table of Contents

- [Overview](#overview)
- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Quick Start](#quick-start)
- [Usage Scenarios](#usage-scenarios)
- [Architecture](#architecture)
- [Detailed Workflows](#detailed-workflows)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

This guide covers the **integrated debugging system** that combines:

- **Phase 1**: Forensic CI Analysis (artifact comparison & analysis)
- **Phase 2**: Local GitHub Actions Simulation (act-based local runs)
- **Integration**: Unified workflow debugging with automatic artifact capture & analysis

### What You Get

✅ **Instant Feedback Loop** - Debug locally without waiting for CI
✅ **Automatic Analysis** - Captures artifacts and runs forensic analysis
✅ **Environment Comparison** - Compares local vs CI environments
✅ **Actionable Recommendations** - Tells you exactly what to fix
✅ **Complete Audit Trail** - Saves all logs, artifacts, and analysis

---

## The Problem

**Traditional CI debugging workflow:**

```
1. Push code → 2. Wait for CI → 3. CI fails → 4. Read logs → 5. Guess the issue
6. Make changes → 7. Push again → 8. Wait again... (repeat 10x)
```

⏱️ **Each cycle takes 5-15 minutes**
😫 **Frustrating and time-consuming**
🎲 **Guesswork-based debugging**

---

## The Solution

**Integrated local debugging workflow:**

```bash
# Single command to debug any job
make -f Makefile.act debug-local JOB=lint-and-format

# Runs the job locally, captures artifacts, analyzes environment,
# and provides recommendations in < 2 minutes
```

✨ **95% faster feedback**
🎯 **Data-driven debugging**
💡 **Automated root cause analysis**

---

## Quick Start

### 1. Setup (One-time)

```bash
# Install act and configure
make -f Makefile.act setup-act

# Validate setup
make -f Makefile.act validate-act
```

### 2. Debug a Job

```bash
# Run a specific job locally with full analysis
make -f Makefile.act debug-local JOB=unit-tests
```

That's it! The system will:
- ✅ Run the job locally with `act`
- ✅ Capture all artifacts
- ✅ Generate environment snapshot
- ✅ Run forensic analysis
- ✅ Provide recommendations

---

## Usage Scenarios

### Scenario 1: Test Fails in CI, Passes Locally

**Problem**: "It works on my machine!"

```bash
# Download the failing CI run
./scripts/download_ci_artifacts.sh 12345678

# Compare local run vs CI run
make -f Makefile.act debug-compare RUN_ID=12345678
```

**What happens**:
1. Downloads CI artifacts
2. Runs same workflow locally
3. Compares environments (variables, dependencies, logs)
4. Highlights differences
5. Recommends fixes

**Example output**:
```
🔴 CRITICAL: DATABASE_URL differs between CI and local
   CI: postgresql://test_user:***@localhost:5432/pake_test
   Local: postgresql://postgres:***@localhost:5432/pake_dev
   → Ensure this variable is set correctly in both environments

📦 5 dependency version mismatches detected:
   • pytest: CI=8.0.0, Local=7.4.3
   → Run: poetry lock && poetry install
```

### Scenario 2: Want to Test Changes Before Pushing

**Problem**: Want to validate changes without waiting for CI

```bash
# Run full CI pipeline locally
make -f Makefile.act simulate-ci

# Or test specific jobs
make -f Makefile.act debug-local JOB=lint-and-format
make -f Makefile.act debug-local JOB=unit-tests
```

**What happens**:
1. Runs workflows in Docker containers (same as GitHub)
2. Uses your local code changes
3. Runs all quality checks
4. Shows results in < 2 minutes

### Scenario 3: Debugging Flaky Tests

**Problem**: Test sometimes passes, sometimes fails

```bash
# Run the test multiple times locally
for i in {1..5}; do
  echo "=== Run $i ==="
  make -f Makefile.act debug-local JOB=e2e-tests
done
```

**What happens**:
1. Each run is logged separately
2. Artifacts captured for each run
3. Can compare differences between runs
4. Helps identify timing/race conditions

### Scenario 4: Validating CI Workflow Changes

**Problem**: Modified `.github/workflows/*.yml` and want to test

```bash
# Test entire workflow file
make -f Makefile.act debug-workflow WORKFLOW=ci.yml
```

**What happens**:
1. Runs the entire workflow locally
2. Shows which jobs pass/fail
3. Captures artifacts from all jobs
4. Validates workflow syntax and logic

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTEGRATED DEBUGGING SYSTEM                  │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐    ┌──────────────────────┐
│   Phase 1: Forensic  │◄──►│   Phase 2: Local     │
│   Analysis Tools     │    │   Simulation (act)   │
└──────────────────────┘    └──────────────────────┘
         │                             │
         │   ┌─────────────────────────┘
         │   │
         ▼   ▼
┌─────────────────────────────┐
│  Integration Layer          │
│  • debug_workflow_local.sh  │
│  • Makefile.act commands    │
│  • Automatic artifact flow  │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Unified Debug Reports      │
│  • Environment comparison   │
│  • Dependency analysis      │
│  • Log analysis             │
│  • Recommendations          │
└─────────────────────────────┘
```

### Data Flow

```
1. User runs: make debug-local JOB=unit-tests
                  │
2. Capture local environment snapshot
                  │
3. Run job with act in Docker
                  │
4. Capture artifacts from local run
                  │
5. Run forensic analysis
                  │
6. Generate comprehensive report
                  │
7. Display actionable recommendations
```

---

## Detailed Workflows

### Integrated Local Debug

**Command**: `make -f Makefile.act debug-local JOB=<name>`

**Steps**:

1. **Validation** (5 sec)
   - Checks Docker is running
   - Checks act is installed
   - Validates configuration files

2. **Environment Snapshot** (10 sec)
   - Captures environment variables
   - Captures pip freeze / poetry dependencies
   - Saves to `./local-snapshot/`

3. **Local Execution** (30-120 sec)
   - Runs job with act
   - Uses Docker containers matching GitHub runners
   - Captures stdout/stderr
   - Saves to `./debug-analysis/act_run_*.log`

4. **Artifact Capture** (5 sec)
   - Copies artifacts from `/tmp/act-artifacts`
   - Organizes by timestamp
   - Saves to `./debug-analysis/artifacts_*/`

5. **Forensic Analysis** (10 sec)
   - Compares local vs captured environment
   - Analyzes dependency versions
   - Scans logs for errors
   - Generates recommendations

6. **Report Generation** (2 sec)
   - Creates debug summary
   - Lists all findings
   - Provides next steps

**Output Files**:
```
debug-analysis/
├── act_run_20251003_142530.log          # Full act execution log
├── artifacts_20251003_142530/            # Captured artifacts
│   ├── environment.log
│   ├── requirements.ci.log
│   ├── pytest_output.xml
│   └── coverage.xml
├── analysis_report_20251003_142530.json # Forensic analysis
├── analysis_20251003_142530.log          # Analysis log
└── debug_summary_20251003_142530.md      # Human-readable summary
```

### Compare Local vs CI

**Command**: `make -f Makefile.act debug-compare RUN_ID=<id>`

**Steps**:

1. **Download CI Artifacts** (30 sec)
   - Uses GitHub CLI to download artifacts
   - Saves to `./ci-artifacts/`

2. **Run Locally** (60-120 sec)
   - Runs same workflow locally
   - Captures artifacts

3. **Dual Analysis** (20 sec)
   - Analyzes CI artifacts
   - Analyzes local artifacts
   - Compares side-by-side

4. **Report Differences** (5 sec)
   - Environment variable diffs
   - Dependency version diffs
   - Log pattern diffs

**Example Report**:
```
ENVIRONMENT DIFFERENCES:
  DATABASE_URL: CI uses test_user, Local uses postgres
  REDIS_URL: Match ✓

DEPENDENCY DIFFERENCES:
  pytest: CI=8.0.0, Local=7.4.3 ❌
  sqlalchemy: Match ✓

LOG ANALYSIS:
  CI: Failed at line 145 with ModuleNotFoundError
  Local: Passed all tests ✓

RECOMMENDATION:
  1. Update DATABASE_URL locally to match CI
  2. Run: poetry lock && poetry install
```

---

## Troubleshooting

### Issue: "act is not installed"

```bash
# Install act
make -f Makefile.act setup-act

# Or manually:
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

### Issue: "Docker is not running"

```bash
# Start Docker Desktop (GUI)
# Or via CLI:
sudo systemctl start docker  # Linux
open -a Docker              # macOS
```

### Issue: "No artifacts captured"

**Possible causes**:
1. Workflow doesn't upload artifacts
2. Artifact paths incorrect

**Solution**:
```bash
# Check if workflow has upload-artifact steps
grep -r "upload-artifact" .github/workflows/

# Add artifact upload to workflow:
- name: Upload diagnostic artifacts
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: |
      reports/
      *.log
```

### Issue: "Analysis shows no differences but CI still fails"

**Possible causes**:
1. Timing/race conditions
2. External service dependencies
3. Platform-specific issues (Linux vs Mac)

**Solution**:
```bash
# Run multiple times to check for flakiness
for i in {1..5}; do
  make -f Makefile.act debug-local JOB=<job-name>
done

# Check for external dependencies
grep -E "(curl|wget|api\.)" .github/workflows/*.yml
```

### Issue: "Out of disk space"

```bash
# Clean up act artifacts
make -f Makefile.act clean-act

# More aggressive cleanup
docker system prune -a --volumes
```

---

## Best Practices

### 1. Always Generate Local Snapshot First

```bash
# Before debugging
python scripts/forensic_ci_analysis.py --generate-local
```

This ensures the most accurate comparison.

### 2. Use Debug Mode for Complex Issues

```bash
# Instead of:
make -f Makefile.act debug-local JOB=unit-tests

# Use:
./scripts/debug_workflow_local.sh unit-tests
```

The script provides more verbose output and better error messages.

### 3. Save Debug Sessions

```bash
# Debug sessions are auto-saved to:
ls -la debug-analysis/

# Archive important sessions
tar -czf debug-$(date +%Y%m%d).tar.gz debug-analysis/
```

### 4. Compare Apples to Apples

When comparing local vs CI, ensure you're testing:
- Same branch
- Same commit
- Same workflow file

### 5. Incremental Debugging

Don't try to fix everything at once:

```bash
# 1. First fix linting
make -f Makefile.act debug-local JOB=lint-and-format

# 2. Then static analysis
make -f Makefile.act debug-local JOB=static-analysis

# 3. Then tests
make -f Makefile.act debug-local JOB=unit-tests
```

### 6. Document Your Findings

The system generates markdown summaries. Add your notes:

```bash
# Edit the summary
vim debug-analysis/debug_summary_*.md

# Add to commit message when fixing
git commit -m "fix: Resolve CI failure in unit tests

Root cause: pytest version mismatch (7.4.3 vs 8.0.0)
Debug session: debug-analysis/debug_summary_20251003_142530.md
"
```

---

## Advanced Features

### Custom Act Configuration

Edit `.actrc` to customize behavior:

```ini
# Use larger runner image
-P ubuntu-latest=catthehacker/ubuntu:full-22.04

# Increase verbosity
--verbose

# Custom artifact path
--artifact-server-path /custom/path
```

### Environment Overrides

```bash
# Override specific variables
ACT_DATABASE_URL="postgresql://custom" make debug-local JOB=unit-tests

# Use custom secrets file
act --secret-file .secrets.dev -j unit-tests
```

### Selective Job Testing

```bash
# Run specific test category
act -j unit-tests --matrix test-category:unit_functional

# Run with specific Python version
act -j unit-tests --matrix python-version:3.12
```

### Integration with Git Hooks

Add to `.git/hooks/pre-push`:

```bash
#!/bin/bash
echo "Running pre-push validation..."
make -f Makefile.act smoke-test

if [ $? -ne 0 ]; then
  echo "Validation failed. Push aborted."
  exit 1
fi
```

---

## Performance Tips

### 1. Pull Images Once

```bash
# Pre-pull Docker images (one time)
make -f Makefile.act pull-images
```

This speeds up subsequent runs by 30-60 seconds.

### 2. Reuse Containers

act reuses containers when possible. Don't clean after every run:

```bash
# Only clean when needed
make -f Makefile.act clean-act
```

### 3. Use Dry Run for Quick Validation

```bash
# Fast syntax check
make -f Makefile.act dry-run
```

### 4. Test Specific Jobs, Not Full Workflows

```bash
# Faster (30 sec)
make -f Makefile.act debug-local JOB=lint-and-format

# Slower (5 min)
make -f Makefile.act simulate-ci
```

---

## Reference

### All Available Commands

```bash
# Setup
make -f Makefile.act setup-act           # Install act
make -f Makefile.act validate-act        # Validate setup
make -f Makefile.act pull-images         # Download Docker images

# Testing
make -f Makefile.act test-lint          # Run linting
make -f Makefile.act test-static        # Run static analysis
make -f Makefile.act test-unit          # Run unit tests
make -f Makefile.act test-all           # Run all quality gates

# Debugging (Integrated)
make -f Makefile.act debug-local JOB=<name>      # 🔬 Run + Analyze
make -f Makefile.act debug-compare RUN_ID=<id>  # 🔬 Compare local vs CI
make -f Makefile.act debug-workflow WORKFLOW=<> # 🔬 Debug entire workflow

# Utilities
make -f Makefile.act list-jobs          # List available jobs
make -f Makefile.act clean-act          # Cleanup
make -f Makefile.act troubleshoot       # Run diagnostics
```

### File Locations

| File | Purpose |
|------|---------|
| `.actrc` | act configuration |
| `.secrets` | Local secrets (not committed) |
| `.vars` | Environment variables |
| `Makefile.act` | Convenience commands |
| `scripts/debug_workflow_local.sh` | Integrated debugger |
| `scripts/forensic_ci_analysis.py` | Analysis engine |
| `scripts/download_ci_artifacts.sh` | CI artifact downloader |
| `debug-analysis/` | Debug output directory |
| `/tmp/act-artifacts/` | act artifact storage |

---

## FAQ

**Q: Does act work on Apple Silicon (M1/M2/M3)?**

A: Yes, but add `--container-architecture linux/amd64` to `.actrc` (already configured).

**Q: Can I debug private repos?**

A: Yes, use `gh auth login` and ensure `.secrets` has `GITHUB_TOKEN`.

**Q: How do I test with specific service versions?**

A: Modify service versions in workflow YAML or use `make start-services` with custom images.

**Q: What if my test needs external APIs?**

A: Add API tokens to `.secrets` and ensure network access in Docker.

**Q: Can I debug Windows-specific workflows?**

A: act only supports Linux containers. For Windows, use GitHub Actions directly.

---

## Next Steps

1. ✅ Complete setup: `make -f Makefile.act setup-act`
2. ✅ Validate: `make -f Makefile.act validate-act`
3. ✅ Try a debug session: `make -f Makefile.act debug-local JOB=lint-and-format`
4. ✅ Compare with CI: `make -f Makefile.act debug-compare RUN_ID=<id>`
5. ✅ Integrate into your workflow

---

**Happy Debugging! 🔬**

For more information:
- Phase 1 Details: `docs/CI_FORENSIC_ANALYSIS.md`
- Phase 2 Details: `docs/PHASE_2_ENVIRONMENTAL_PARITY_GUIDE.md`
- Quick Reference: `CI_DEBUG_QUICK_REFERENCE.md`
