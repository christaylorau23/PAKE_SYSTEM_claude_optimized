"""
Performance Monitoring and Reporting Scripts
===========================================

This module provides comprehensive performance monitoring, reporting,
and alerting capabilities for the PAKE System.

Features:
- Performance baseline establishment
- Trend analysis and degradation detection
- Automated reporting and alerting
- Performance threshold validation
"""

import json
import time
import requests  # type: ignore
import statistics
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta
import argparse


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: str
    environment: str
    test_type: str
    scenario: str
    total_requests: int
    failed_requests: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate_percent: float
    concurrent_users: int
    test_duration_seconds: int


@dataclass
class PerformanceThresholds:
    """Performance thresholds configuration"""
    max_response_time_ms: float = 2000.0
    max_error_rate_percent: float = 5.0
    min_throughput_rps: float = 10.0
    max_p95_response_time_ms: float = 1000.0
    max_p99_response_time_ms: float = 1500.0


class PerformanceMonitor:
    """Monitors performance metrics and detects degradation"""

    def __init__(self, results_dir: str = "performance_tests/results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.baseline_file = self.results_dir / "performance_baseline.json"
        self.thresholds_file = self.results_dir / "performance_thresholds.json"
        self.baseline: Optional[PerformanceMetrics] = None
        self.thresholds: PerformanceThresholds = PerformanceThresholds()
        self.load_baseline()
        self.load_thresholds()

    def load_baseline(self):
        """Load performance baseline"""
        if self.baseline_file.exists():
            with open(self.baseline_file, 'r') as f:
                baseline_data = json.load(f)
                self.baseline = PerformanceMetrics(**baseline_data)
                print(f"Loaded baseline from {self.baseline_file}")
        else:
            print("No baseline found - will create one after first test")

    def load_thresholds(self):
        """Load performance thresholds"""
        if self.thresholds_file.exists():
            with open(self.thresholds_file, 'r') as f:
                thresholds_data = json.load(f)
                self.thresholds = PerformanceThresholds(**thresholds_data)
                print(f"Loaded thresholds from {self.thresholds_file}")
        else:
            self.save_thresholds()

    def save_baseline(self, metrics: PerformanceMetrics):
        """Save performance baseline"""
        with open(self.baseline_file, 'w') as f:
            json.dump(asdict(metrics), f, indent=2)
        self.baseline = metrics
        print(f"Saved baseline to {self.baseline_file}")

    def save_thresholds(self):
        """Save performance thresholds"""
        with open(self.thresholds_file, 'w') as f:
            json.dump(asdict(self.thresholds), f, indent=2)
        print(f"Saved thresholds to {self.thresholds_file}")

    def validate_performance(self, metrics: PerformanceMetrics) -> Dict[str, bool]:
        """Validate performance against thresholds"""
        validation = {}

        # Check response time
        avg_response_time_ms = metrics.avg_response_time * 1000
        validation["response_time"] = avg_response_time_ms <= self.thresholds.max_response_time_ms

        # Check error rate
        validation["error_rate"] = metrics.error_rate_percent <= self.thresholds.max_error_rate_percent

        # Check throughput
        validation["throughput"] = metrics.requests_per_second >= self.thresholds.min_throughput_rps

        # Check P95 response time
        p95_response_time_ms = metrics.p95_response_time * 1000
        validation["p95_response_time"] = p95_response_time_ms <= self.thresholds.max_p95_response_time_ms

        # Check P99 response time
        p99_response_time_ms = metrics.p99_response_time * 1000
        validation["p99_response_time"] = p99_response_time_ms <= self.thresholds.max_p99_response_time_ms

        validation["overall"] = all(validation.values())

        return validation

    def detect_degradation(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Detect performance degradation compared to baseline"""
        if not self.baseline:
            return {"degradation_detected": False, "message": "No baseline available"}

        degradation = {
            "degradation_detected": False,
            "metrics": {},
            "severity": "none",
            "message": ""
        }

        # Compare key metrics
        response_time_ratio = metrics.avg_response_time / self.baseline.avg_response_time
        error_rate_increase = metrics.error_rate_percent - self.baseline.error_rate_percent
        throughput_ratio = metrics.requests_per_second / self.baseline.requests_per_second

        degradation["metrics"] = {
            "response_time_ratio": response_time_ratio,
            "error_rate_increase": error_rate_increase,
            "throughput_ratio": throughput_ratio
        }

        # Determine severity
        if response_time_ratio > 2.0 or error_rate_increase > 10.0 or throughput_ratio < 0.5:
            degradation["severity"] = "critical"
            degradation["degradation_detected"] = True
            degradation["message"] = "Critical performance degradation detected"
        elif response_time_ratio > 1.5 or error_rate_increase > 5.0 or throughput_ratio < 0.7:
            degradation["severity"] = "high"
            degradation["degradation_detected"] = True
            degradation["message"] = "High performance degradation detected"
        elif response_time_ratio > 1.2 or error_rate_increase > 2.0 or throughput_ratio < 0.9:
            degradation["severity"] = "medium"
            degradation["degradation_detected"] = True
            degradation["message"] = "Medium performance degradation detected"
        elif response_time_ratio > 1.1 or error_rate_increase > 1.0 or throughput_ratio < 0.95:
            degradation["severity"] = "low"
            degradation["degradation_detected"] = True
            degradation["message"] = "Low performance degradation detected"

        return degradation

    def update_baseline(self, metrics: PerformanceMetrics):
        """Update baseline with new metrics"""
        if not self.baseline:
            self.save_baseline(metrics)
            print("Created new baseline")
        else:
            # Update baseline with weighted average
            alpha = 0.1  # Learning rate
            updated_metrics = PerformanceMetrics(
                timestamp=metrics.timestamp,
                environment=metrics.environment,
                test_type=metrics.test_type,
                scenario=metrics.scenario,
                total_requests=int(self.baseline.total_requests * (1 - alpha) + metrics.total_requests * alpha),
                failed_requests=int(self.baseline.failed_requests * (1 - alpha) + metrics.failed_requests * alpha),
                avg_response_time=self.baseline.avg_response_time * (1 - alpha) + metrics.avg_response_time * alpha,
                max_response_time=max(self.baseline.max_response_time, metrics.max_response_time),
                min_response_time=min(self.baseline.min_response_time, metrics.min_response_time),
                p95_response_time=self.baseline.p95_response_time * (1 - alpha) + metrics.p95_response_time * alpha,
                p99_response_time=self.baseline.p99_response_time * (1 - alpha) + metrics.p99_response_time * alpha,
                requests_per_second=self.baseline.requests_per_second * (1 - alpha) + metrics.requests_per_second * alpha,
                error_rate_percent=self.baseline.error_rate_percent * (1 - alpha) + metrics.error_rate_percent * alpha,
                concurrent_users=metrics.concurrent_users,
                test_duration_seconds=metrics.test_duration_seconds
            )
            self.save_baseline(updated_metrics)
            print("Updated baseline")


class PerformanceReporter:
    """Generates comprehensive performance reports"""

    def __init__(self, results_dir: str = "performance_tests/results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, metrics: PerformanceMetrics,
                       validation: Dict[str, bool],
                       degradation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive performance report"""

        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "report_version": "1.0.0",
                "environment": metrics.environment,
                "test_type": metrics.test_type,
                "scenario": metrics.scenario
            },
            "performance_metrics": asdict(metrics),
            "performance_validation": validation,
            "degradation_analysis": degradation,
            "recommendations": self._generate_recommendations(metrics, validation, degradation),
            "summary": self._generate_summary(metrics, validation, degradation)
        }

        return report

    def _generate_recommendations(self, metrics: PerformanceMetrics,
                                validation: Dict[str, bool],
                                degradation: Dict[str, Any]) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []

        # Response time recommendations
        if not validation.get("response_time", True):
            recommendations.append(
                f"Response time ({metrics.avg_response_time:.2f}s) exceeds threshold. "
                "Consider optimizing database queries, adding caching, or scaling resources."
            )

        # Error rate recommendations
        if not validation.get("error_rate", True):
            recommendations.append(
                f"Error rate ({metrics.error_rate_percent:.2f}%) exceeds threshold. "
                "Investigate error logs, improve error handling, and add circuit breakers."
            )

        # Throughput recommendations
        if not validation.get("throughput", True):
            recommendations.append(
                f"Throughput ({metrics.requests_per_second:.2f} RPS) below threshold. "
                "Consider horizontal scaling, load balancing, or performance optimization."
            )

        # Degradation recommendations
        if degradation.get("degradation_detected", False):
            severity = degradation.get("severity", "unknown")
            recommendations.append(
                f"Performance degradation detected (severity: {severity}). "
                "Review recent changes, monitor resource usage, and consider rollback."
            )

        # General recommendations
        if metrics.p99_response_time > metrics.avg_response_time * 3:
            recommendations.append(
                "High P99 response time indicates performance variability. "
                "Consider optimizing slow queries and reducing tail latency."
            )

        if not recommendations:
            recommendations.append("Performance metrics are within acceptable ranges.")

        return recommendations

    def _generate_summary(self, metrics: PerformanceMetrics,
                         validation: Dict[str, bool],
                         degradation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance summary"""

        overall_status = "healthy"
        if not validation.get("overall", True):
            overall_status = "degraded"
        if degradation.get("degradation_detected", False):
            severity = degradation.get("severity", "unknown")
            if severity in ["critical", "high"]:
                overall_status = "critical"
            elif severity == "medium":
                overall_status = "degraded"

        return {
            "overall_status": overall_status,
            "key_metrics": {
                "avg_response_time_ms": metrics.avg_response_time * 1000,
                "error_rate_percent": metrics.error_rate_percent,
                "throughput_rps": metrics.requests_per_second,
                "p95_response_time_ms": metrics.p95_response_time * 1000,
                "p99_response_time_ms": metrics.p99_response_time * 1000
            },
            "validation_passed": validation.get("overall", False),
            "degradation_detected": degradation.get("degradation_detected", False),
            "degradation_severity": degradation.get("severity", "none")
        }

    def save_report(self, report: Dict[str, Any], filename: Optional[str] = None):
        """Save performance report to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"

        filepath = self.results_dir / filename

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Performance report saved to: {filepath}")
        return filepath


class PerformanceAlerting:
    """Handles performance alerting and notifications"""

    def __init__(self, slack_webhook_url: Optional[str] = None):
        self.slack_webhook_url = slack_webhook_url

    def send_alert(self, report: Dict[str, Any], severity: str = "medium"):
        """Send performance alert"""
        if not self.slack_webhook_url:
            print("No Slack webhook URL configured - alert not sent")
            return

        summary = report.get("summary", {})
        overall_status = summary.get("overall_status", "unknown")

        # Determine alert color
        color_map = {
            "healthy": "good",
            "degraded": "warning",
            "critical": "danger"
        }
        color = color_map.get(overall_status, "warning")

        # Create alert message
        alert_message = {
            "attachments": [
                {
                    "color": color,
                    "title": f"PAKE System Performance Alert - {overall_status.upper()}",
                    "fields": [
                        {
                            "title": "Environment",
                            "value": report["report_metadata"]["environment"],
                            "short": True
                        },
                        {
                            "title": "Test Scenario",
                            "value": report["report_metadata"]["scenario"],
                            "short": True
                        },
                        {
                            "title": "Avg Response Time",
                            "value": f"{summary['key_metrics']['avg_response_time_ms']:.0f}ms",
                            "short": True
                        },
                        {
                            "title": "Error Rate",
                            "value": f"{summary['key_metrics']['error_rate_percent']:.2f}%",
                            "short": True
                        },
                        {
                            "title": "Throughput",
                            "value": f"{summary['key_metrics']['throughput_rps']:.1f} RPS",
                            "short": True
                        },
                        {
                            "title": "P95 Response Time",
                            "value": f"{summary['key_metrics']['p95_response_time_ms']:.0f}ms",
                            "short": True
                        }
                    ],
                    "footer": "PAKE System Performance Monitor",
                    "ts": int(time.time())
                }
            ]
        }

        # Add recommendations if any
        recommendations = report.get("recommendations", [])
        if recommendations:
            fields = alert_message["attachments"][0]["fields"]
            if isinstance(fields, list):
                fields.append({
                    "title": "Recommendations",
                    "value": "\n".join(recommendations[:3]),  # Limit to first 3 recommendations
                    "short": False
                })

        try:
            response = requests.post(self.slack_webhook_url, json=alert_message)
            if response.status_code == 200:
                print("Performance alert sent successfully")
            else:
                print(f"Failed to send alert: {response.status_code}")
        except Exception as e:
            print(f"Error sending alert: {e}")


def main():
    """Main function for performance monitoring"""
    parser = argparse.ArgumentParser(description="PAKE System Performance Monitor")
    parser.add_argument("--environment", "-e", default="production",
                       choices=["local", "staging", "production"],
                       help="Target environment")
    parser.add_argument("--thresholds", "-t",
                       default="performance_tests/config/performance_thresholds.json",
                       help="Performance thresholds file")
    parser.add_argument("--slack-webhook", "-s",
                       help="Slack webhook URL for alerts")
    parser.add_argument("--update-baseline", "-b", action="store_true",
                       help="Update performance baseline")

    args = parser.parse_args()

    # Initialize monitor
    monitor = PerformanceMonitor()

    # Load thresholds if provided
    if Path(args.thresholds).exists():
        with open(args.thresholds, 'r') as f:
            thresholds_data = json.load(f)
            monitor.thresholds = PerformanceThresholds(**thresholds_data)

    # Initialize reporter and alerting
    reporter = PerformanceReporter()
    alerting = PerformanceAlerting(args.slack_webhook)

    # For demo purposes, create sample metrics
    # In production, this would come from actual test results
    sample_metrics = PerformanceMetrics(
        timestamp=datetime.now().isoformat(),
        environment=args.environment,
        test_type="load",
        scenario="normal",
        total_requests=1000,
        failed_requests=25,
        avg_response_time=1.2,
        max_response_time=5.0,
        min_response_time=0.1,
        p95_response_time=2.0,
        p99_response_time=3.0,
        requests_per_second=15.0,
        error_rate_percent=2.5,
        concurrent_users=100,
        test_duration_seconds=600
    )

    # Validate performance
    validation = monitor.validate_performance(sample_metrics)

    # Detect degradation
    degradation = monitor.detect_degradation(sample_metrics)

    # Generate report
    report = reporter.generate_report(sample_metrics, validation, degradation)

    # Save report
    report_file = reporter.save_report(report)

    # Update baseline if requested
    if args.update_baseline:
        monitor.update_baseline(sample_metrics)

    # Send alert if degradation detected
    if degradation.get("degradation_detected", False):
        alerting.send_alert(report, degradation.get("severity", "medium"))

    # Print summary
    print("\n" + "="*60)
    print("PERFORMANCE MONITORING SUMMARY")
    print("="*60)
    print(f"Environment: {sample_metrics.environment}")
    print(f"Overall Status: {report['summary']['overall_status'].upper()}")
    print(f"Avg Response Time: {sample_metrics.avg_response_time:.2f}s")
    print(f"Error Rate: {sample_metrics.error_rate_percent:.2f}%")
    print(f"Throughput: {sample_metrics.requests_per_second:.1f} RPS")
    print(f"Validation Passed: {'✅' if validation.get('overall') else '❌'}")
    print(f"Degradation Detected: {'⚠️' if degradation.get('degradation_detected') else '✅'}")
    print(f"Report saved to: {report_file}")


if __name__ == "__main__":
    main()
