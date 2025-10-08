# PAKE System - Code Quality Dashboard Setup

## Overview
This document provides the complete setup for a comprehensive code quality dashboard that tracks technical debt, security posture, and development velocity metrics for the PAKE System.

## Dashboard Architecture

### Primary Dashboard: SonarQube Cloud
**Purpose:** Enterprise-grade quality monitoring and technical debt quantification
**Status:** Recommended for implementation
**Benefits:**
- Technical debt measurement in remediation hours
- Quality gate automation
- Trend analysis and historical tracking
- Integration with CI/CD pipeline

### Secondary Dashboard: Custom Metrics Dashboard
**Purpose:** Real-time monitoring and custom KPIs
**Status:** Can be implemented alongside SonarQube
**Benefits:**
- Custom metrics specific to PAKE System
- Real-time alerts and notifications
- Integration with existing monitoring stack

---

## SonarQube Cloud Configuration

### Project Setup
```yaml
# sonar-project.properties
sonar.projectKey=pake-system
sonar.organization=your-org
sonar.projectName=PAKE System
sonar.projectVersion=1.0.0

# Source code configuration
sonar.sources=src
sonar.tests=tests
sonar.python.coverage.reportPaths=coverage.xml
sonar.python.bandit.reportPaths=bandit_report.json

# Quality gate configuration
sonar.qualitygate.wait=true
```

### GitHub Actions Integration
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

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest-cov bandit

      - name: Run tests with coverage
        run: |
          pytest --cov=src --cov-report=xml --cov-report=term

      - name: Run security scan
        run: |
          bandit -r src/ -f json -o bandit_report.json

      - name: SonarCloud Scan
        uses: SonarSource/sonarcloud-github-action@master
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

---

## Custom Metrics Dashboard

### Dashboard Components

#### 1. Technical Debt Overview
```python
# dashboard/technical_debt_metrics.py
from dataclasses import dataclass
from typing import Dict, List
import subprocess
import json
from datetime import datetime

@dataclass
class TechnicalDebtMetrics:
    """Technical debt metrics for dashboard"""
    total_violations: int
    critical_issues: int
    security_issues: int
    test_coverage: float
    last_updated: datetime

    def calculate_debt_ratio(self) -> float:
        """Calculate technical debt ratio"""
        return self.total_violations / 1000  # Normalize to 1000 lines

    def get_trend(self, historical_data: List['TechnicalDebtMetrics']) -> str:
        """Calculate trend direction"""
        if len(historical_data) < 2:
            return "insufficient_data"

        latest = historical_data[-1].total_violations
        previous = historical_data[-2].total_violations

        if latest < previous:
            return "improving"
        elif latest > previous:
            return "deteriorating"
        else:
            return "stable"

class QualityMetricsCollector:
    """Collects quality metrics from various tools"""

    def collect_ruff_metrics(self) -> Dict[str, int]:
        """Collect Ruff linting metrics"""
        result = subprocess.run(
            ["ruff", "check", "--statistics"],
            capture_output=True, text=True
        )

        metrics = {}
        for line in result.stdout.split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 2:
                    count = int(parts[0])
                    rule = parts[1].strip()
                    metrics[rule] = count

        return metrics

    def collect_security_metrics(self) -> Dict[str, int]:
        """Collect Bandit security metrics"""
        result = subprocess.run(
            ["bandit", "-r", "src/", "-f", "json"],
            capture_output=True, text=True
        )

        data = json.loads(result.stdout)
        metrics = {
            "total": len(data["results"]),
            "high": len([r for r in data["results"] if r["issue_severity"] == "HIGH"]),
            "medium": len([r for r in data["results"] if r["issue_severity"] == "MEDIUM"]),
            "low": len([r for r in data["results"] if r["issue_severity"] == "LOW"])
        }

        return metrics

    def collect_coverage_metrics(self) -> float:
        """Collect test coverage metrics"""
        result = subprocess.run(
            ["pytest", "--cov=src", "--cov-report=term-missing", "-q"],
            capture_output=True, text=True
        )

        # Parse coverage from output
        for line in result.stdout.split('\n'):
            if 'TOTAL' in line and '%' in line:
                coverage_str = line.split()[-1].replace('%', '')
                return float(coverage_str)

        return 0.0
```

#### 2. Security Posture Dashboard
```python
# dashboard/security_metrics.py
from dataclasses import dataclass
from typing import Dict, List
import json
import subprocess

@dataclass
class SecurityMetrics:
    """Security metrics for dashboard"""
    total_issues: int
    high_severity: int
    medium_severity: int
    low_severity: int
    critical_vulnerabilities: List[Dict]
    last_scan: str

    def calculate_security_score(self) -> int:
        """Calculate security score (0-100)"""
        if self.total_issues == 0:
            return 100

        # Penalize high severity issues more heavily
        penalty = (self.high_severity * 10) + (self.medium_severity * 5) + (self.low_severity * 1)
        score = max(0, 100 - penalty)
        return int(score)

    def get_security_trend(self, historical_data: List['SecurityMetrics']) -> str:
        """Calculate security trend"""
        if len(historical_data) < 2:
            return "insufficient_data"

        latest_score = historical_data[-1].calculate_security_score()
        previous_score = historical_data[-2].calculate_security_score()

        if latest_score > previous_score:
            return "improving"
        elif latest_score < previous_score:
            return "deteriorating"
        else:
            return "stable"

class SecurityMetricsCollector:
    """Collects security metrics from Bandit and other tools"""

    def collect_bandit_metrics(self) -> SecurityMetrics:
        """Collect Bandit security metrics"""
        result = subprocess.run(
            ["bandit", "-r", "src/", "-f", "json"],
            capture_output=True, text=True
        )

        data = json.loads(result.stdout)

        high_severity = len([r for r in data["results"] if r["issue_severity"] == "HIGH"])
        medium_severity = len([r for r in data["results"] if r["issue_severity"] == "MEDIUM"])
        low_severity = len([r for r in data["results"] if r["issue_severity"] == "LOW"])

        critical_vulnerabilities = [
            r for r in data["results"]
            if r["issue_severity"] in ["HIGH", "MEDIUM"]
        ]

        return SecurityMetrics(
            total_issues=len(data["results"]),
            high_severity=high_severity,
            medium_severity=medium_severity,
            low_severity=low_severity,
            critical_vulnerabilities=critical_vulnerabilities,
            last_scan=datetime.now().isoformat()
        )
```

#### 3. Development Velocity Metrics
```python
# dashboard/velocity_metrics.py
from dataclasses import dataclass
from typing import Dict, List
import subprocess
from datetime import datetime, timedelta

@dataclass
class VelocityMetrics:
    """Development velocity metrics"""
    commits_per_day: float
    lines_changed_per_commit: float
    test_coverage_trend: str
    build_success_rate: float
    pr_merge_time: float

    def calculate_velocity_score(self) -> int:
        """Calculate velocity score (0-100)"""
        score = 0

        # Commits per day (target: 5-10)
        if 5 <= self.commits_per_day <= 10:
            score += 25
        elif self.commits_per_day > 10:
            score += 20
        else:
            score += 10

        # Test coverage trend
        if self.test_coverage_trend == "improving":
            score += 25
        elif self.test_coverage_trend == "stable":
            score += 20
        else:
            score += 10

        # Build success rate
        score += int(self.build_success_rate * 25)

        # PR merge time (target: <2 days)
        if self.pr_merge_time < 2:
            score += 25
        elif self.pr_merge_time < 5:
            score += 20
        else:
            score += 10

        return min(100, score)

class VelocityMetricsCollector:
    """Collects development velocity metrics"""

    def collect_git_metrics(self, days: int = 30) -> Dict[str, float]:
        """Collect Git-based velocity metrics"""
        # Get commits in last N days
        result = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--oneline"],
            capture_output=True, text=True
        )

        commits = len(result.stdout.strip().split('\n'))
        commits_per_day = commits / days

        # Get lines changed per commit
        result = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--stat"],
            capture_output=True, text=True
        )

        # Parse lines changed (simplified)
        lines_changed = 0
        for line in result.stdout.split('\n'):
            if 'insertion' in line or 'deletion' in line:
                # Extract numbers (simplified parsing)
                numbers = [int(x) for x in line.split() if x.isdigit()]
                lines_changed += sum(numbers)

        lines_changed_per_commit = lines_changed / commits if commits > 0 else 0

        return {
            "commits_per_day": commits_per_day,
            "lines_changed_per_commit": lines_changed_per_commit
        }
```

---

## Dashboard Implementation

### 1. Web Dashboard (Flask/FastAPI)
```python
# dashboard/app.py
from flask import Flask, render_template, jsonify
from dashboard.technical_debt_metrics import QualityMetricsCollector
from dashboard.security_metrics import SecurityMetricsCollector
from dashboard.velocity_metrics import VelocityMetricsCollector
import json

app = Flask(__name__)

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/metrics')
def get_metrics():
    """API endpoint for metrics data"""
    collector = QualityMetricsCollector()
    security_collector = SecurityMetricsCollector()
    velocity_collector = VelocityMetricsCollector()

    metrics = {
        "technical_debt": collector.collect_ruff_metrics(),
        "security": security_collector.collect_bandit_metrics().__dict__,
        "velocity": velocity_collector.collect_git_metrics(),
        "timestamp": datetime.now().isoformat()
    }

    return jsonify(metrics)

@app.route('/api/trends')
def get_trends():
    """API endpoint for trend data"""
    # Load historical data from database or file
    with open('dashboard/historical_data.json', 'r') as f:
        historical_data = json.load(f)

    return jsonify(historical_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### 2. HTML Dashboard Template
```html
<!-- dashboard/templates/dashboard.html -->
<!DOCTYPE html>
<html>
<head>
    <title>PAKE System - Code Quality Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .metric-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin: 10px;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        .metric-label {
            color: #666;
            font-size: 0.9em;
        }
        .trend-up { color: #28a745; }
        .trend-down { color: #dc3545; }
        .trend-stable { color: #ffc107; }
    </style>
</head>
<body>
    <h1>PAKE System - Code Quality Dashboard</h1>

    <div class="dashboard-grid">
        <!-- Technical Debt Card -->
        <div class="metric-card">
            <h3>Technical Debt</h3>
            <div class="metric-value" id="total-violations">-</div>
            <div class="metric-label">Total Violations</div>
            <div id="debt-trend" class="trend-stable">-</div>
        </div>

        <!-- Security Card -->
        <div class="metric-card">
            <h3>Security Posture</h3>
            <div class="metric-value" id="security-score">-</div>
            <div class="metric-label">Security Score</div>
            <div id="security-trend" class="trend-stable">-</div>
        </div>

        <!-- Test Coverage Card -->
        <div class="metric-card">
            <h3>Test Coverage</h3>
            <div class="metric-value" id="test-coverage">-</div>
            <div class="metric-label">Coverage %</div>
            <div id="coverage-trend" class="trend-stable">-</div>
        </div>

        <!-- Development Velocity Card -->
        <div class="metric-card">
            <h3>Development Velocity</h3>
            <div class="metric-value" id="velocity-score">-</div>
            <div class="metric-label">Velocity Score</div>
            <div id="velocity-trend" class="trend-stable">-</div>
        </div>
    </div>

    <!-- Charts -->
    <div class="metric-card">
        <h3>Technical Debt Trend</h3>
        <canvas id="debt-chart" width="400" height="200"></canvas>
    </div>

    <div class="metric-card">
        <h3>Security Issues Trend</h3>
        <canvas id="security-chart" width="400" height="200"></canvas>
    </div>

    <script>
        // Load metrics data
        fetch('/api/metrics')
            .then(response => response.json())
            .then(data => {
                updateDashboard(data);
            });

        function updateDashboard(data) {
            // Update metric cards
            document.getElementById('total-violations').textContent =
                data.technical_debt.total || 0;

            document.getElementById('security-score').textContent =
                data.security.total_issues || 0;

            document.getElementById('test-coverage').textContent =
                data.coverage || 0;

            document.getElementById('velocity-score').textContent =
                data.velocity.commits_per_day || 0;
        }

        // Load trend data and create charts
        fetch('/api/trends')
            .then(response => response.json())
            .then(data => {
                createCharts(data);
            });

        function createCharts(trendData) {
            // Technical Debt Chart
            const debtCtx = document.getElementById('debt-chart').getContext('2d');
            new Chart(debtCtx, {
                type: 'line',
                data: {
                    labels: trendData.dates,
                    datasets: [{
                        label: 'Technical Debt',
                        data: trendData.debt_values,
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });

            // Security Chart
            const securityCtx = document.getElementById('security-chart').getContext('2d');
            new Chart(securityCtx, {
                type: 'bar',
                data: {
                    labels: trendData.dates,
                    datasets: [{
                        label: 'Security Issues',
                        data: trendData.security_values,
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    </script>
</body>
</html>
```

---

## Monitoring & Alerting

### Alert Configuration
```python
# dashboard/alerts.py
from dataclasses import dataclass
from typing import List, Dict
import smtplib
from email.mime.text import MIMEText

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    condition: str
    threshold: float
    severity: str
    enabled: bool

class AlertManager:
    """Manages alerts and notifications"""

    def __init__(self):
        self.rules = [
            AlertRule(
                name="High Security Issues",
                condition="security.high_severity > 0",
                threshold=0,
                severity="critical",
                enabled=True
            ),
            AlertRule(
                name="Technical Debt Increase",
                condition="technical_debt.total > previous * 1.2",
                threshold=1.2,
                severity="warning",
                enabled=True
            ),
            AlertRule(
                name="Test Coverage Drop",
                condition="coverage < 80",
                threshold=80,
                severity="warning",
                enabled=True
            )
        ]

    def check_alerts(self, metrics: Dict) -> List[Dict]:
        """Check all alert rules and return triggered alerts"""
        triggered_alerts = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            if self.evaluate_condition(rule.condition, metrics):
                triggered_alerts.append({
                    "rule": rule.name,
                    "severity": rule.severity,
                    "message": f"Alert: {rule.name} triggered",
                    "timestamp": datetime.now().isoformat()
                })

        return triggered_alerts

    def send_notification(self, alert: Dict):
        """Send notification for triggered alert"""
        # Email notification
        msg = MIMEText(alert["message"])
        msg['Subject'] = f"PAKE System Alert: {alert['rule']}"
        msg['From'] = "alerts@pake-system.com"
        msg['To'] = "engineering-team@pake-system.com"

        # Send email (configure SMTP server)
        # smtp_server.send_message(msg)

        # Slack notification
        # webhook_url = "https://hooks.slack.com/services/..."
        # requests.post(webhook_url, json={"text": alert["message"]})
```

---

## Implementation Timeline

### Week 1: Basic Dashboard
- [ ] Set up Flask dashboard application
- [ ] Implement basic metrics collection
- [ ] Create HTML dashboard template
- [ ] Test local dashboard functionality

### Week 2: SonarQube Integration
- [ ] Configure SonarQube Cloud project
- [ ] Set up GitHub Actions integration
- [ ] Configure quality gates
- [ ] Test automated analysis

### Week 3: Advanced Features
- [ ] Implement trend analysis
- [ ] Add chart visualizations
- [ ] Set up alerting system
- [ ] Configure notifications

### Week 4: Production Deployment
- [ ] Deploy dashboard to production
- [ ] Set up monitoring and logging
- [ ] Train team on dashboard usage
- [ ] Document maintenance procedures

---

## Success Metrics

### Dashboard Adoption
- **Team Usage:** 100% of engineering team using dashboard daily
- **Alert Response:** <5 minutes average response time to critical alerts
- **Data Accuracy:** 99%+ accuracy in metrics collection

### Quality Improvement
- **Technical Debt:** Measurable reduction in debt ratio
- **Security Posture:** Zero high-severity security issues
- **Test Coverage:** Maintain 80%+ coverage

### Process Improvement
- **Decision Making:** Data-driven quality decisions
- **Trend Analysis:** Clear visibility into quality trends
- **Proactive Management:** Early detection of quality issues

---

**Dashboard Setup Generated:** January 2025
**Next Review:** Scheduled for 30 days post-implementation
**Owner:** Engineering Team
**Maintenance:** Automated via CI/CD pipeline
