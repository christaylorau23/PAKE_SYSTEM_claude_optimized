# CI Debug Quick Reference 🚀

## 🆘 Test Failed in CI? 3-Step Fix

### Step 1: Download Artifacts (30 seconds)
```bash
./scripts/download_ci_artifacts.sh
```

### Step 2: Generate Local Snapshot (10 seconds)
```bash
python scripts/forensic_ci_analysis.py --generate-local
```

### Step 3: Run Analysis (5 seconds)
```bash
python scripts/forensic_ci_analysis.py --artifacts-dir ./ci-artifacts/[artifact-name]
```

---

## 🔥 Common Issues & Instant Fixes

### ❌ ModuleNotFoundError
```bash
# The report will show missing module
# Fix: Add to pyproject.toml
poetry add <package-name>
poetry lock && poetry install
```

### ❌ FileNotFoundError
```bash
# Usually case-sensitivity (CI=Linux, Local=Mac/Win)
# Fix: Check exact file casing
git ls-files | grep -i "filename"
```

### ❌ Environment Variable Mismatch
```bash
# The report highlights different values
# Fix: Update .env or GitHub Secrets
# .env: DATABASE_URL=postgresql://...
```

### ❌ Dependency Version Mismatch
```bash
# Report shows: pytest: CI=8.0.0, Local=7.4.3
# Fix: Sync dependencies
poetry lock
poetry install
```

### ❌ Timeout Error
```python
# Fix: Increase timeout in pytest.ini or test
@pytest.mark.timeout(60)  # CI needs more time
def test_slow_operation():
    pass
```

---

## 📋 Analysis Report TL;DR

Look for these sections in order:

1. **🔴 CRITICAL** recommendations → Fix these first
2. **Environment Variable** differences → Check DATABASE_URL, SECRET_KEY
3. **Dependency** mismatches → Run `poetry lock && poetry install`
4. **Log Issues** → Find first error (ignore cascading failures)

---

## 🎯 Download Specific Run

```bash
# Get run ID from GitHub Actions URL
# Example: https://github.com/user/repo/actions/runs/12345678
./scripts/download_ci_artifacts.sh 12345678
```

---

## 🛠️ Script Locations

| Tool | Location | Purpose |
|------|----------|---------|
| Artifact Downloader | `scripts/download_ci_artifacts.sh` | Download CI artifacts |
| Forensic Analyzer | `scripts/forensic_ci_analysis.py` | Compare CI vs Local |
| Full Guide | `docs/CI_FORENSIC_ANALYSIS.md` | Detailed documentation |

---

## 💡 Pro Tips

- **First error matters** - Scroll up in logs to find root cause
- **Check critical env vars** - DATABASE_URL, REDIS_URL, SECRET_KEY
- **Case matters on Linux** - CI is case-sensitive, Mac/Windows aren't
- **Save JSON reports** - Add `--output-json report.json` to track history

---

## 🚨 Emergency Checklist

- [ ] Downloaded latest CI artifacts
- [ ] Generated local environment snapshot
- [ ] Ran forensic analysis
- [ ] Fixed critical issues from recommendations
- [ ] Synced dependencies (`poetry lock && poetry install`)
- [ ] Verified environment variables match
- [ ] Pushed fix and reran CI

---

**Full Documentation**: See `docs/CI_FORENSIC_ANALYSIS.md` for comprehensive guide.
