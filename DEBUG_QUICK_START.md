# 🚀 CI/CD Debugging Quick Start

**The fastest way to debug CI failures - locally!**

---

## ⚡ 30-Second Setup

```bash
# 1. Install act
make -f Makefile.act setup-act

# 2. Configure secrets (edit with your values)
vim .secrets

# 3. Validate
make -f Makefile.act validate-act
```

Done! You're ready to debug.

---

## 🔥 Most Common Use Cases

### 1️⃣ Test Failed in CI → Debug Locally

```bash
# Single command to reproduce + analyze
make -f Makefile.act debug-local JOB=unit-tests
```

**What happens:**
- ✅ Runs job locally in Docker (same as GitHub)
- ✅ Captures artifacts automatically
- ✅ Analyzes environment differences
- ✅ Tells you exactly what's wrong

**Time:** < 2 minutes vs 10+ minutes waiting for CI

---

### 2️⃣ Works Locally, Fails in CI → Compare Environments

```bash
# Get the failing CI run ID from GitHub Actions URL
# Example: https://github.com/user/repo/actions/runs/12345678
#                                                    ^^^^^^^^

make -f Makefile.act debug-compare RUN_ID=12345678
```

**What happens:**
- ✅ Downloads CI artifacts
- ✅ Runs same workflow locally
- ✅ Compares environments side-by-side
- ✅ Highlights differences (env vars, dependencies, etc.)

**Common findings:**
```
🔴 DATABASE_URL differs between CI and local
📦 pytest version mismatch: CI=8.0.0, Local=7.4.3
🔴 Module 'src.services.caching' not found in CI
```

---

### 3️⃣ Want to Test Before Pushing

```bash
# Run full CI pipeline locally
make -f Makefile.act simulate-ci

# Or test specific checks
make -f Makefile.act test-lint       # Linting
make -f Makefile.act test-static     # Type checking
make -f Makefile.act test-unit       # Unit tests
```

**Benefit:** Catch issues before pushing (saves CI minutes!)

---

## 🎯 Command Cheat Sheet

| Task | Command | Time |
|------|---------|------|
| Debug one job | `make -f Makefile.act debug-local JOB=<name>` | 1-2 min |
| Compare vs CI | `make -f Makefile.act debug-compare RUN_ID=<id>` | 2-3 min |
| Run full CI | `make -f Makefile.act simulate-ci` | 5-10 min |
| List all jobs | `make -f Makefile.act list-jobs` | instant |
| Quick smoke test | `make -f Makefile.act smoke-test` | 30 sec |

---

## 🛠️ Available Jobs

```bash
# See all jobs you can run
make -f Makefile.act list-jobs
```

Common jobs:
- `lint-and-format` - Code quality checks
- `static-analysis` - Type checking & security
- `unit-tests` - Unit test suite
- `integration-tests` - Integration tests
- `e2e-tests` - End-to-end tests
- `security-scan` - Security scanning

---

## 💡 Pro Tips

### Tip 1: Always Check Differences First

```bash
# If CI fails, first compare environments
make -f Makefile.act debug-compare RUN_ID=<failing-run-id>

# The report will tell you exactly what's different
```

### Tip 2: Fix Issues Incrementally

```bash
# Don't run everything at once
# Fix issues one by one:

make -f Makefile.act debug-local JOB=lint-and-format  # Fix linting first
make -f Makefile.act debug-local JOB=static-analysis  # Then type errors
make -f Makefile.act debug-local JOB=unit-tests       # Then tests
```

### Tip 3: Review Debug Reports

All debug sessions are saved to `./debug-analysis/`:

```bash
# Latest debug summary
ls -t debug-analysis/debug_summary_*.md | head -1 | xargs cat

# Latest forensic analysis
ls -t debug-analysis/analysis_report_*.json | head -1 | xargs cat | jq '.recommendations'
```

---

## 🆘 Troubleshooting

### "act is not installed"

```bash
make -f Makefile.act setup-act
```

### "Docker is not running"

```bash
# Start Docker Desktop, then retry
```

### "No artifacts found"

Normal if the job doesn't generate artifacts. The analysis will still work.

### Still stuck?

```bash
# Run diagnostics
make -f Makefile.act troubleshoot

# Read full guide
cat docs/INTEGRATED_DEBUGGING_GUIDE.md
```

---

## 📚 Documentation

- **This file** - Quick start (you are here)
- `docs/INTEGRATED_DEBUGGING_GUIDE.md` - Complete guide
- `docs/CI_FORENSIC_ANALYSIS.md` - Phase 1 details
- `docs/PHASE_2_ENVIRONMENTAL_PARITY_GUIDE.md` - Phase 2 details
- `CI_DEBUG_QUICK_REFERENCE.md` - Legacy quick reference

---

## 🎬 Example Session

```bash
# 1. A test failed in CI
$ gh run list --limit 1
STATUS  NAME        WORKFLOW  RUN ID
✗       CI Pipeline  CI        12345678

# 2. Debug locally
$ make -f Makefile.act debug-local JOB=unit-tests

🔬 Running integrated local debug for job: unit-tests
✅ Prerequisites validated
📸 Generating local environment snapshot...
🚀 Running workflow locally with act...
📦 Capturing artifacts from local run...
🔬 Running forensic analysis...

📋 FORENSIC CI ANALYSIS REPORT
================================================================================

📦 DEPENDENCY ANALYSIS:
⚠️  1 version mismatches:
   • pytest: CI=8.0.0, Local=7.4.3

💡 RECOMMENDATIONS:
1. 📦 1 dependency version mismatches detected:
   • pytest: CI=8.0.0, Local=7.4.3
   → Run: poetry lock && poetry install

# 3. Fix the issue
$ poetry lock && poetry install

# 4. Verify fix
$ make -f Makefile.act debug-local JOB=unit-tests
✅ Workflow succeeded locally!

# 5. Push with confidence
$ git push
```

---

## 🚀 Next Steps

1. **Setup**: Run `make -f Makefile.act setup-act`
2. **Try it**: Run `make -f Makefile.act debug-local JOB=lint-and-format`
3. **Master it**: Read `docs/INTEGRATED_DEBUGGING_GUIDE.md`

**You're now equipped to debug 95% faster than traditional CI debugging!** 🎉
