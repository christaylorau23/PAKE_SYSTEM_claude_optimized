# CI Forensic Analysis Guide

Comprehensive guide for debugging CI test failures using automated forensic analysis tools.

## 🎯 Overview

When tests pass locally but fail in CI, systematic forensic analysis is required to identify the root cause. This guide covers:

1. **Automatic environment comparison** (CI vs Local)
2. **Dependency mismatch detection**
3. **Log pattern analysis** for errors, timeouts, and file issues
4. **Actionable recommendations** based on findings

## 🛠️ Tools

### 1. Forensic CI Analysis Script
**Location**: `scripts/forensic_ci_analysis.py`

Automates comparison between CI and local environments, analyzing:
- Environment variable differences
- Python dependency version mismatches
- Log files for errors, timeouts, and module/file issues
- Generates prioritized recommendations

### 2. Artifact Downloader
**Location**: `scripts/download_ci_artifacts.sh`

Downloads diagnostic artifacts from GitHub Actions runs for offline analysis.

## 📋 Quick Start

### Step 1: Download CI Artifacts

```bash
# Download from latest failed run
./scripts/download_ci_artifacts.sh

# Download from specific run
./scripts/download_ci_artifacts.sh 12345678
```

This downloads all diagnostic artifacts to `./ci-artifacts/`

### Step 2: Generate Local Snapshot

```bash
python scripts/forensic_ci_analysis.py --generate-local
```

This captures your local environment to `./local-snapshot/`:
- `environment.log` - Environment variables
- `requirements.ci.log` - Installed packages (pip freeze)
- `poetry.tree.log` - Poetry dependency tree

### Step 3: Run Forensic Analysis

```bash
# Analyze CI artifacts against local environment
python scripts/forensic_ci_analysis.py \
    --artifacts-dir ./ci-artifacts/[artifact-name] \
    --output-json analysis-report.json
```

## 📊 Analysis Report Sections

### 1. Environment Variable Analysis

Identifies differences in environment variables between CI and local:

```
🌍 ENVIRONMENT VARIABLE ANALYSIS:
--------------------------------------------------------------------------------

⚠️  3 variables with different values:
   • DATABASE_URL
     CI:    postgresql://test_user:test_password@localhost:5432/pake_test
     Local: postgresql://postgres:postgres@localhost:5432/pake_dev

   • SECRET_KEY
     CI:    test-secret-key-for-ci
     Local: dev-secret-key-local
```

**Common Issues**:
- Missing critical environment variables (DATABASE_URL, REDIS_URL, SECRET_KEY)
- Different values for the same variable
- CI-specific variables not needed locally

### 2. Dependency Analysis

Detects version mismatches and missing packages:

```
📦 DEPENDENCY ANALYSIS:
--------------------------------------------------------------------------------

⚠️  5 version mismatches:
   • pytest: CI=8.0.0, Local=7.4.3
   • sqlalchemy: CI=2.0.25, Local=2.0.23
   • redis: CI=5.0.1, Local=5.0.0
```

**Common Issues**:
- Different package versions between CI and local
- Packages installed in CI but not locally (or vice versa)
- Transitive dependency conflicts

### 3. Log Analysis

Scans logs for error patterns:

```
🔎 LOG ANALYSIS:
--------------------------------------------------------------------------------

MODULE NOT FOUND: 2 found

   Line 145: ModuleNotFoundError: No module named 'src.services.caching'
   Context:
      File "/home/runner/work/tests/test_integration.py", line 23
      from src.services.caching import RedisCache
      ModuleNotFoundError: No module named 'src.services.caching'

TIMEOUT: 1 found

   Line 892: TimeoutError: Connection to Redis timed out after 30s
```

**Detected Patterns**:
- `ModuleNotFoundError` - Missing Python packages
- `FileNotFoundError` - Missing files or case-sensitivity issues
- Timeout errors - Performance/resource constraints
- General exceptions and tracebacks

### 4. Recommendations

Prioritized action items:

```
💡 RECOMMENDATIONS:
================================================================================

1. 🔴 CRITICAL: Module 'src.services.caching' not found (line 145)
   → Check if package is in pyproject.toml
   → Run: poetry add src

2. 📦 5 dependency version mismatches detected:
   • pytest: CI=8.0.0, Local=7.4.3
   • sqlalchemy: CI=2.0.25, Local=2.0.23
   → Run: poetry lock && poetry install

3. 🔴 CRITICAL: DATABASE_URL differs between CI and local
   CI: postgresql://test_user:***@localhost:5432/pake_test
   Local: postgresql://postgres:***@localhost:5432/pake_dev
   → Ensure this variable is set correctly in both environments
```

## 🔍 Advanced Usage

### Compare Specific Artifact Directory

```bash
python scripts/forensic_ci_analysis.py \
    --artifacts-dir ./ci-artifacts/unit-test-results-unit_functional
```

### Save Results to JSON

```bash
python scripts/forensic_ci_analysis.py \
    --artifacts-dir ./ci-artifacts/unit-test-results \
    --output-json detailed-report.json
```

### Generate Local Snapshot Only

```bash
python scripts/forensic_ci_analysis.py \
    --generate-local \
    --local-snapshot-dir ./my-env-snapshot
```

## 🐛 Common Root Causes & Solutions

### 1. Environment Variable Differences

**Symptom**: Tests fail with configuration errors or connection issues

**Investigation**:
```bash
# Compare environment.log from CI with local env
diff ci-artifacts/environment.log <(env | sort)
```

**Solution**:
- Add missing variables to `.env` file
- Update CI secrets/variables in GitHub Settings
- Ensure test fixtures use consistent values

### 2. Dependency Version Mismatches

**Symptom**: Import errors, API changes, unexpected behavior

**Investigation**:
```bash
# Compare package versions
diff ci-artifacts/requirements.ci.log <(pip freeze)
```

**Solution**:
```bash
# Sync dependencies
poetry lock
poetry install

# Or update specific package
poetry update pytest
```

### 3. Case-Sensitivity Issues

**Symptom**: `FileNotFoundError` in CI but works locally

**Investigation**:
- Look for files with inconsistent casing
- Check import statements vs actual file names

**Solution**:
```bash
# Find case-sensitivity issues
git ls-files | grep -i "filename"

# Fix imports to match exact casing
# Example: fix 'from src.Services' to 'from src.services'
```

### 4. Path Resolution Issues

**Symptom**: `ModuleNotFoundError` for internal packages

**Investigation**:
```bash
# Check PYTHONPATH differences
grep PYTHONPATH ci-artifacts/environment.log
echo $PYTHONPATH
```

**Solution**:
- Ensure `src/` is in PYTHONPATH
- Use absolute imports: `from src.services.x import Y`
- Add `__init__.py` files to packages

### 5. Timing/Timeout Issues

**Symptom**: Tests timeout in CI but not locally

**Investigation**:
- Look for "took X.XXs" messages in logs
- Check connection timeouts
- Review resource-intensive operations

**Solution**:
```python
# Increase timeouts for CI
@pytest.mark.timeout(60 if os.getenv("CI") else 30)
def test_slow_operation():
    pass

# Or use pytest.ini
[pytest]
timeout = 60
```

### 6. Missing Test Dependencies

**Symptom**: Tests fail with import errors

**Investigation**:
```bash
# Check if dev dependencies are installed
poetry show --tree | grep pytest
```

**Solution**:
```bash
# Ensure dev dependencies are installed
poetry install --with dev

# Update CI workflow
- name: Install dependencies
  run: poetry install --no-interaction --with dev
```

## 📁 Artifact Structure

After running the downloader, artifacts are organized as:

```
ci-artifacts/
├── unit-test-results-unit_functional/
│   ├── unit-test-results-unit_functional.xml
│   ├── coverage.xml
│   ├── htmlcov/
│   ├── environment.log              ← Environment variables
│   ├── requirements.ci.log          ← Installed packages
│   └── poetry.tree.log             ← Dependency tree
├── integration-test-results-integration/
│   └── ...
└── e2e-test-results-e2e_user_journey/
    └── ...
```

## 🎯 Workflow Integration

### GitHub Actions Workflow Changes

The CI workflows now include:

```yaml
- name: Capture environment snapshot
  run: |
    mkdir -p reports logs
    echo "--- Environment Variables ---" > environment.log
    env >> environment.log
    echo "\n--- Python Packages (pip freeze) ---" > requirements.ci.log
    pip freeze >> requirements.ci.log
    echo "\n--- Poetry Dependency Tree ---" > poetry.tree.log
    poetry show --tree >> poetry.tree.log

- name: Run tests
  run: |
    pytest tests/ --junitxml=reports/junit.xml -vv

- name: Upload diagnostic artifacts
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: diagnostic-artifacts
    path: |
      reports/
      logs/
      environment.log
      requirements.ci.log
      poetry.tree.log
```

## 📈 Analysis Workflow

```mermaid
graph TD
    A[Test Fails in CI] --> B[Download Artifacts]
    B --> C[Generate Local Snapshot]
    C --> D[Run Forensic Analysis]
    D --> E{Issue Found?}
    E -->|Environment Diff| F[Update .env / CI Secrets]
    E -->|Dependency Mismatch| G[Run poetry lock && install]
    E -->|Module Not Found| H[Add to pyproject.toml]
    E -->|File Not Found| I[Check Case Sensitivity]
    E -->|Timeout| J[Increase Timeout / Optimize]
    F --> K[Rerun CI]
    G --> K
    H --> K
    I --> K
    J --> K
```

## 🔧 Troubleshooting

### GitHub CLI Not Authenticated

```bash
gh auth login
```

### No Artifacts Found

Ensure your CI workflow includes artifact upload steps:

```yaml
- name: Upload diagnostic artifacts
  if: always()
  uses: actions/upload-artifact@v4
```

### Python Import Errors in Analysis Script

```bash
# The script is standalone and has no external dependencies
python3 scripts/forensic_ci_analysis.py --help
```

### Permission Denied

```bash
chmod +x scripts/*.sh
chmod +x scripts/*.py
```

## 📚 References

- [GitHub Actions Artifacts](https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts)
- [GitHub CLI](https://cli.github.com/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [pytest Documentation](https://docs.pytest.org/)

## 💡 Best Practices

1. **Always generate local snapshot first** - Ensures accurate comparison
2. **Focus on first error** - Subsequent errors are often cascading
3. **Check critical environment variables** - DATABASE_URL, SECRET_KEY, etc.
4. **Verify dependency versions match** - Use `poetry lock` to sync
5. **Look for case-sensitivity** - CI runs on Linux (case-sensitive)
6. **Increase verbosity** - Use `-vv` for detailed test output
7. **Save analysis reports** - Use `--output-json` for historical tracking

## 🚀 Next Steps

After identifying and fixing issues:

1. **Update CI workflow** if needed
2. **Document findings** in commit message
3. **Add regression tests** to prevent recurrence
4. **Update this guide** with new patterns discovered

---

**Need Help?** Open an issue or consult the team lead.
