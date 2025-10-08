# PAKE System - Static Analysis Tool Configuration

## Overview
This document provides the complete configuration for static analysis tools integrated into the PAKE System CI/CD pipeline, following the engineering plan's "Prophylactic Fortification" phase.

## Tool Configuration Status

### ✅ Ruff (Primary Linter & Formatter)
**Status:** Configured and operational
**Configuration:** `/home/chris/PAKE_SYSTEM_claude_optimized/pyproject.toml`
**Purpose:** High-velocity linting and formatting

#### Key Ruleset (Based on Table 4.1 from Engineering Plan)
```toml
[tool.ruff.lint]
select = [
    # Critical bug prevention rules
    "F821",    # UndefinedName - Directly prevents F821 errors
    "DTZ003",  # CallDatetimeNowWithoutTzinfo - Prevents naive datetime objects
    "DTZ004",  # CallDatetimeFromtimestampWithoutTzinfo - Prevents naive datetime objects
    "DTZ005",  # CallDatetimeUTCNow - Crucially forbids datetime.utcnow()
    "G004",    # LoggingFString - Discourages f-strings in logs, pushes to structlog

    # Security rules (Bandit integration)
    "S",       # flake8-bandit - All security rules integrated

    # Code quality and maintainability
    "B",       # flake8-bugbear
    "C4",      # flake8-comprehensions
    "UP",      # pyupgrade
    "ARG",     # flake8-unused-arguments
    "SIM",     # flake8-simplify
    "TCH",     # flake8-type-checking
    "TID",     # flake8-tidy-imports
    "Q",       # flake8-quotes
    "I",       # isort
    "N",       # pep8-naming
    "D",       # pydocstyle
    "A",       # flake8-builtins
    "COM",     # flake8-commas
    "EM",      # flake8-errmsg
    "EXE",     # flake8-executable
    "FA",      # flake8-future-annotations
    "ISC",     # flake8-implicit-str-concat
    "ICN",     # flake8-import-conventions
    "G",       # flake8-logging-format
    "INP",     # flake8-no-pep420
    "PIE",     # flake8-pie
    "T20",     # flake8-print
    "PYI",     # flake8-pyi
    "PT",      # flake8-pytest-style
    "RSE",     # flake8-raise
    "RET",     # flake8-return
    "SLF",     # flake8-self
    "SLOT",    # flake8-slots
    "YTT",     # flake8-2020
]
```

#### Current Violations Summary
- **Total Violations:** 5,174
- **Critical Issues:** 142 F821 errors
- **Security Issues:** 191 total (0 High, 24 Medium, 167 Low)
- **Code Quality:** 4,841 other violations

### ✅ Bandit (Security Analysis)
**Status:** Configured and operational
**Configuration:** `/home/chris/PAKE_SYSTEM_claude_optimized/pyproject.toml`
**Purpose:** Static Application Security Testing (SAST)

#### Configuration
```toml
[tool.bandit]
exclude_dirs = ["tests", "venv", ".venv", "mcp-env", "test_env", "security_backups", "backups"]
skips = ["B101", "B601"]
```

#### Security Analysis Results
- **Total Issues:** 191
- **High Severity:** 0 ✅
- **Medium Severity:** 24 ⚠️
- **Low Severity:** 167 ℹ️

#### Key Security Findings
- **S311:** 153 instances of weak cryptographic random usage
- **S603:** 36 instances of subprocess calls requiring review
- **S101:** 64 instances of assert statements
- **S607:** 59 instances of process execution with partial paths

### ⚠️ SonarQube/SonarCloud (Enterprise Dashboard)
**Status:** Recommended for implementation
**Purpose:** Comprehensive quality dashboarding and technical debt quantification

#### Recommended Configuration
```yaml
# .github/workflows/sonarcloud.yml
name: SonarCloud Analysis
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  sonarcloud:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: SonarCloud Scan
        uses: SonarSource/sonarcloud-github-action@master
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

#### Expected Benefits
- **Technical Debt Quantification:** Measure remediation time in hours
- **Quality Gates:** Automated pass/fail criteria
- **Trend Analysis:** Track improvement over time
- **Hotspot Identification:** Focus on high-impact areas

---

## CI/CD Pipeline Integration

### GitHub Actions Workflow
**File:** `.github/workflows/quality.yml`

```yaml
name: Quality Gates
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v3
        with:
          args: "check"

  format:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v3
        with:
          args: "format --check"

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Bandit Security Scan
        run: |
          pip install bandit
          bandit -r src/ -f json -o bandit_report.json
          bandit -r src/ -f txt
```

### Pre-commit Hooks Configuration
**File:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: [-r, src/]
```

---

## Quality Gate Thresholds

### Phase 1: Observe (Current)
- **Ruff:** Report violations (non-blocking)
- **Bandit:** Report security issues (non-blocking)
- **Tests:** Report collection errors (non-blocking)

### Phase 2: Enforce on New Code (Recommended)
- **Ruff:** Block PR if new violations introduced
- **Bandit:** Block PR if new high/medium security issues
- **Tests:** Block PR if test coverage < 80% on new code
- **Coverage:** Block PR if coverage decreases

### Phase 3: Gradually Tighten (Future)
- **Ruff:** Enforce on modified files only
- **Bandit:** Require security review for all findings
- **Tests:** Increase coverage threshold to 85%
- **Performance:** Add performance regression detection

---

## Monitoring & Reporting

### Code Quality Dashboard
**Recommended:** SonarQube Cloud integration

#### Key Metrics to Track
1. **Technical Debt Ratio:** Hours of remediation time
2. **Code Coverage:** Percentage of lines covered by tests
3. **Security Hotspots:** High-risk security areas
4. **Code Smells:** Maintainability issues
5. **Duplicated Code:** Percentage of duplicated lines

### Automated Reporting
```python
# scripts/quality_report.py
import json
import subprocess
from datetime import datetime

def generate_quality_report():
    """Generate comprehensive quality report"""

    # Run Ruff analysis
    ruff_result = subprocess.run(
        ["ruff", "check", "--statistics"],
        capture_output=True, text=True
    )

    # Run Bandit analysis
    bandit_result = subprocess.run(
        ["bandit", "-r", "src/", "-f", "json"],
        capture_output=True, text=True
    )

    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "ruff_violations": parse_ruff_output(ruff_result.stdout),
        "security_issues": json.loads(bandit_result.stdout),
        "trends": calculate_trends()
    }

    return report
```

---

## Implementation Roadmap

### Week 1: Tool Configuration
- [x] Configure Ruff ruleset
- [x] Configure Bandit security scanning
- [ ] Set up SonarQube Cloud integration
- [ ] Configure pre-commit hooks

### Week 2: CI/CD Integration
- [ ] Create GitHub Actions workflow
- [ ] Set up quality gates
- [ ] Configure automated reporting
- [ ] Test pipeline integration

### Week 3: Monitoring Setup
- [ ] Create quality dashboard
- [ ] Set up trend monitoring
- [ ] Configure alerting
- [ ] Train team on tools

### Week 4: Optimization
- [ ] Fine-tune rules and thresholds
- [ ] Optimize performance
- [ ] Document processes
- [ ] Establish maintenance procedures

---

## Success Metrics

### Immediate (30 days)
- **Tool Integration:** 100% of tools operational
- **Quality Gates:** Automated checks on all PRs
- **Security Scanning:** Continuous security monitoring

### Short-term (90 days)
- **Violation Reduction:** 80% reduction in critical issues
- **Coverage Improvement:** 80%+ test coverage
- **Security Posture:** Zero high-severity issues

### Long-term (6 months)
- **Technical Debt:** Quantified and trending downward
- **Development Velocity:** Measurable improvement
- **System Reliability:** Reduced production incidents

---

## Maintenance Procedures

### Daily
- Monitor quality gate failures
- Review security scan results
- Check test coverage trends

### Weekly
- Analyze violation trends
- Review security findings
- Update tool configurations

### Monthly
- Comprehensive quality report
- Tool performance optimization
- Process improvement review

---

**Configuration Generated:** January 2025
**Next Review:** Scheduled for 30 days post-implementation
**Owner:** Engineering Team
**Maintenance:** Automated via CI/CD pipeline
