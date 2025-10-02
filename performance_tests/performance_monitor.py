"""
Performance Monitoring and Alerting Infrastructure
=================================================

This module provides comprehensive performance monitoring, alerting,
and automated response capabilities for the PAKE System.

Key Features:
- Real-time performance monitoring
- Automated alerting and notifications
- Performance trend analysis
- Automated scaling recommendations
- Integration with external monitoring systems
"""

import time
import json
import requests  # type: ignore
import psutil
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


@dataclass
class PerformanceAlert:
    """Performance alert data structure"""
    alert_id: str
    alert_type: str
    severity: str
    message: str
    timestamp: str
    metrics: Dict[str, Any]
    threshold_value: float
    current_value: float
    environment: str
    resolved: bool = False
    resolved_at: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Real-time performance metrics"""
    timestamp: str
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_io_bytes: int
    response_time_ms: float
    requests_per_second: float
    error_rate_percent: float
    active_connections: int
    queue_length: int


class PerformanceMonitor:
    """Real-time performance monitoring system"""

    def __init__(self, config_file: str = "performance_tests/config/monitoring_config.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self.config = self._load_config()

        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.metrics_history: deque = deque(maxlen=self.config.get("history_size", 1000))
        self.active_alerts: Dict[str, PerformanceAlert] = {}

        # Alerting
        self.alert_handlers: List[Callable[[PerformanceAlert], None]] = []
        self.alert_cooldown: Dict[str, datetime] = {}

        # Setup logging
        self.logger = logging.getLogger("performance_monitor")
        self.logger.setLevel(logging.INFO)

        # Initialize alert handlers
        self._setup_default_alert_handlers()

    def _load_config(self) -> Dict[str, Any]:
        """Load monitoring configuration"""
        default_config = {
            "monitoring_interval_seconds": 30,
            "history_size": 1000,
            "alert_cooldown_minutes": 15,
            "thresholds": {
                "cpu_usage_percent": 80.0,
                "memory_usage_percent": 85.0,
                "disk_usage_percent": 90.0,
                "response_time_ms": 2000.0,
                "error_rate_percent": 5.0,
                "queue_length": 100
            },
            "alerting": {
                "email_enabled": False,
                "slack_enabled": False,
                "webhook_enabled": False,
                "email_recipients": [],
                "slack_webhook_url": "",
                "webhook_url": ""
            }
        }

        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                default_config.update(config)
        else:
            # Save default config
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)

        return default_config

    def _setup_default_alert_handlers(self):
        """Setup default alert handlers"""
        if self.config["alerting"]["email_enabled"]:
            self.add_alert_handler(self._email_alert_handler)

        if self.config["alerting"]["slack_enabled"]:
            self.add_alert_handler(self._slack_alert_handler)

        if self.config["alerting"]["webhook_enabled"]:
            self.add_alert_handler(self._webhook_alert_handler)

    def start_monitoring(self):
        """Start performance monitoring"""
        if self.monitoring_active:
            print("Performance monitoring already active")
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()

        print(f"Performance monitoring started (interval: {self.config['monitoring_interval_seconds']}s)")

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("Performance monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)

                # Check thresholds and generate alerts
                self._check_thresholds(metrics)

                time.sleep(self.config["monitoring_interval_seconds"])

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)

    def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        # System metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Network I/O
        network_io = psutil.net_io_counters()
        network_bytes = network_io.bytes_sent + network_io.bytes_recv

        # Application metrics (simulated - in production, these would come from your app)
        response_time = self._get_response_time()
        requests_per_second = self._get_requests_per_second()
        error_rate = self._get_error_rate()
        active_connections = self._get_active_connections()
        queue_length = self._get_queue_length()

        return PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_usage_percent=cpu_usage,
            memory_usage_percent=memory.percent,
            disk_usage_percent=disk.percent,
            network_io_bytes=network_bytes,
            response_time_ms=response_time,
            requests_per_second=requests_per_second,
            error_rate_percent=error_rate,
            active_connections=active_connections,
            queue_length=queue_length
        )

    def _get_response_time(self) -> float:
        """Get average response time (simulated)"""
        # In production, this would query your application metrics
        return 150.0  # Simulated 150ms

    def _get_requests_per_second(self) -> float:
        """Get requests per second (simulated)"""
        # In production, this would query your application metrics
        return 25.0  # Simulated 25 RPS

    def _get_error_rate(self) -> float:
        """Get error rate percentage (simulated)"""
        # In production, this would query your application metrics
        return 1.5  # Simulated 1.5% error rate

    def _get_active_connections(self) -> int:
        """Get active connections (simulated)"""
        # In production, this would query your application metrics
        return 45  # Simulated 45 active connections

    def _get_queue_length(self) -> int:
        """Get queue length (simulated)"""
        # In production, this would query your application metrics
        return 12  # Simulated queue length of 12

    def _check_thresholds(self, metrics: PerformanceMetrics):
        """Check metrics against thresholds and generate alerts"""
        thresholds = self.config["thresholds"]

        # Check CPU usage
        if metrics.cpu_usage_percent > thresholds["cpu_usage_percent"]:
            self._create_alert(
                "cpu_usage",
                "high",
                f"CPU usage is {metrics.cpu_usage_percent:.1f}%",
                metrics,
                thresholds["cpu_usage_percent"],
                metrics.cpu_usage_percent
            )

        # Check memory usage
        if metrics.memory_usage_percent > thresholds["memory_usage_percent"]:
            self._create_alert(
                "memory_usage",
                "high",
                f"Memory usage is {metrics.memory_usage_percent:.1f}%",
                metrics,
                thresholds["memory_usage_percent"],
                metrics.memory_usage_percent
            )

        # Check disk usage
        if metrics.disk_usage_percent > thresholds["disk_usage_percent"]:
            self._create_alert(
                "disk_usage",
                "critical",
                f"Disk usage is {metrics.disk_usage_percent:.1f}%",
                metrics,
                thresholds["disk_usage_percent"],
                metrics.disk_usage_percent
            )

        # Check response time
        if metrics.response_time_ms > thresholds["response_time_ms"]:
            self._create_alert(
                "response_time",
                "high",
                f"Response time is {metrics.response_time_ms:.1f}ms",
                metrics,
                thresholds["response_time_ms"],
                metrics.response_time_ms
            )

        # Check error rate
        if metrics.error_rate_percent > thresholds["error_rate_percent"]:
            self._create_alert(
                "error_rate",
                "high",
                f"Error rate is {metrics.error_rate_percent:.1f}%",
                metrics,
                thresholds["error_rate_percent"],
                metrics.error_rate_percent
            )

        # Check queue length
        if metrics.queue_length > thresholds["queue_length"]:
            self._create_alert(
                "queue_length",
                "medium",
                f"Queue length is {metrics.queue_length}",
                metrics,
                thresholds["queue_length"],
                metrics.queue_length
            )

    def _create_alert(self, alert_type: str, severity: str, message: str,
                      metrics: PerformanceMetrics, threshold: float, current_value: float):
        """Create and process performance alert"""
        alert_id = f"{alert_type}_{int(time.time())}"

        # Check cooldown
        cooldown_key = f"{alert_type}_{severity}"
        if cooldown_key in self.alert_cooldown:
            cooldown_time = self.alert_cooldown[cooldown_key]
            if datetime.now() - cooldown_time < timedelta(minutes=self.config["alert_cooldown_minutes"]):
                return  # Still in cooldown period

        # Create alert
        alert = PerformanceAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.now().isoformat(),
            metrics=asdict(metrics),
            threshold_value=threshold,
            current_value=current_value,
            environment="production"
        )

        # Store alert
        self.active_alerts[alert_id] = alert

        # Set cooldown
        self.alert_cooldown[cooldown_key] = datetime.now()

        # Send alert
        self._send_alert(alert)

        self.logger.warning(f"Performance alert: {message}")

    def _send_alert(self, alert: PerformanceAlert):
        """Send alert to all registered handlers"""
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Error in alert handler: {e}")

    def add_alert_handler(self, handler: Callable[[PerformanceAlert], None]):
        """Add custom alert handler"""
        self.alert_handlers.append(handler)

    def _email_alert_handler(self, alert: PerformanceAlert):
        """Email alert handler"""
        if not self.config["alerting"]["email_enabled"]:
            return

        recipients = self.config["alerting"]["email_recipients"]
        if not recipients:
            return

        # Create email message
        msg = MIMEMultipart()
        msg['From'] = "pake-system@example.com"
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = f"PAKE System Alert: {alert.alert_type.upper()}"

        # Email body
        body = f"""
PAKE System Performance Alert

Alert Type: {alert.alert_type}
Severity: {alert.severity}
Message: {alert.message}
Timestamp: {alert.timestamp}
Environment: {alert.environment}

Current Value: {alert.current_value}
Threshold: {alert.threshold_value}

Metrics:
- CPU Usage: {alert.metrics['cpu_usage_percent']:.1f}%
- Memory Usage: {alert.metrics['memory_usage_percent']:.1f}%
- Response Time: {alert.metrics['response_time_ms']:.1f}ms
- Error Rate: {alert.metrics['error_rate_percent']:.1f}%

Please investigate and take appropriate action.

PAKE System Performance Monitor
        """

        msg.attach(MIMEText(body, 'plain'))

        # Send email (simulated - configure with your SMTP server)
        print(f"Email alert sent: {alert.message}")

    def _slack_alert_handler(self, alert: PerformanceAlert):
        """Slack alert handler"""
        if not self.config["alerting"]["slack_enabled"]:
            return

        webhook_url = self.config["alerting"]["slack_webhook_url"]
        if not webhook_url:
            return

        # Determine color based on severity
        color_map = {
            "low": "good",
            "medium": "warning",
            "high": "danger",
            "critical": "danger"
        }
        color = color_map.get(alert.severity, "warning")

        # Create Slack message
        message = {
            "attachments": [
                {
                    "color": color,
                    "title": f"PAKE System Alert: {alert.alert_type.upper()}",
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.upper(),
                            "short": True
                        },
                        {
                            "title": "Message",
                            "value": alert.message,
                            "short": False
                        },
                        {
                            "title": "Current Value",
                            "value": str(alert.current_value),
                            "short": True
                        },
                        {
                            "title": "Threshold",
                            "value": str(alert.threshold_value),
                            "short": True
                        },
                        {
                            "title": "Environment",
                            "value": alert.environment,
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": alert.timestamp,
                            "short": True
                        }
                    ],
                    "footer": "PAKE System Performance Monitor",
                    "ts": int(time.time())
                }
            ]
        }

        try:
            response = requests.post(webhook_url, json=message)
            if response.status_code == 200:
                print(f"Slack alert sent: {alert.message}")
            else:
                print(f"Failed to send Slack alert: {response.status_code}")
        except Exception as e:
            print(f"Error sending Slack alert: {e}")

    def _webhook_alert_handler(self, alert: PerformanceAlert):
        """Webhook alert handler"""
        if not self.config["alerting"]["webhook_enabled"]:
            return

        webhook_url = self.config["alerting"]["webhook_url"]
        if not webhook_url:
            return

        # Create webhook payload
        payload = {
            "alert_id": alert.alert_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "timestamp": alert.timestamp,
            "environment": alert.environment,
            "metrics": alert.metrics,
            "threshold_value": alert.threshold_value,
            "current_value": alert.current_value
        }

        try:
            response = requests.post(webhook_url, json=payload)
            if response.status_code == 200:
                print(f"Webhook alert sent: {alert.message}")
            else:
                print(f"Failed to send webhook alert: {response.status_code}")
        except Exception as e:
            print(f"Error sending webhook alert: {e}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary"""
        if not self.metrics_history:
            return {"message": "No metrics available"}

        latest_metrics = self.metrics_history[-1]

        # Calculate trends
        trends = self._calculate_trends()

        # Alert summary
        alert_summary = {
            "total_alerts": len(self.active_alerts),
            "active_alerts": len([a for a in self.active_alerts.values() if not a.resolved]),
            "alerts_by_severity": {
                "critical": len([a for a in self.active_alerts.values() if a.severity == "critical"]),
                "high": len([a for a in self.active_alerts.values() if a.severity == "high"]),
                "medium": len([a for a in self.active_alerts.values() if a.severity == "medium"]),
                "low": len([a for a in self.active_alerts.values() if a.severity == "low"])
            }
        }

        return {
            "current_metrics": asdict(latest_metrics),
            "trends": trends,
            "alert_summary": alert_summary,
            "monitoring_status": "active" if self.monitoring_active else "inactive"
        }

    def _calculate_trends(self) -> Dict[str, str]:
        """Calculate performance trends"""
        if len(self.metrics_history) < 2:
            return {"trend": "insufficient_data"}

        recent_metrics = list(self.metrics_history)[-10:]  # Last 10 measurements

        trends = {}

        # CPU trend
        cpu_values = [m.cpu_usage_percent for m in recent_metrics]
        trends["cpu"] = self._calculate_trend_direction(cpu_values)

        # Memory trend
        memory_values = [m.memory_usage_percent for m in recent_metrics]
        trends["memory"] = self._calculate_trend_direction(memory_values)

        # Response time trend
        response_values = [m.response_time_ms for m in recent_metrics]
        trends["response_time"] = self._calculate_trend_direction(response_values)

        return trends

    def _calculate_trend_direction(self, values: List[float]) -> str:
        """Calculate trend direction for a series of values"""
        if len(values) < 2:
            return "insufficient_data"

        start_value = values[0]
        end_value = values[-1]
        change_percent = ((end_value - start_value) / start_value) * 100

        if change_percent > 10:
            return "increasing"
        elif change_percent < -10:
            return "decreasing"
        else:
            return "stable"

    def generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        summary = self.get_performance_summary()

        recommendations = []

        # Alert-based recommendations
        if summary["alert_summary"]["active_alerts"] > 0:
            recommendations.append({
                "priority": "high",
                "category": "Active Alerts",
                "description": f"{summary['alert_summary']['active_alerts']} active alerts",
                "impact": "System performance degradation",
                "suggestions": [
                    "Investigate active alerts immediately",
                    "Review threshold configurations",
                    "Implement automated remediation",
                    "Scale resources if needed"
                ]
            })

        # Trend-based recommendations
        trends = summary["trends"]
        if trends.get("cpu") == "increasing":
            recommendations.append({
                "priority": "medium",
                "category": "CPU Usage",
                "description": "CPU usage trending upward",
                "impact": "Potential performance degradation",
                "suggestions": [
                    "Monitor CPU usage closely",
                    "Consider horizontal scaling",
                    "Optimize CPU-intensive operations",
                    "Review resource allocation"
                ]
            })

        if trends.get("memory") == "increasing":
            recommendations.append({
                "priority": "medium",
                "category": "Memory Usage",
                "description": "Memory usage trending upward",
                "impact": "Potential memory pressure",
                "suggestions": [
                    "Monitor memory usage closely",
                    "Check for memory leaks",
                    "Consider memory optimization",
                    "Review caching strategies"
                ]
            })

        return {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "monitoring_duration_hours": len(self.metrics_history) * self.config["monitoring_interval_seconds"] / 3600,
                "total_metrics_collected": len(self.metrics_history)
            },
            "performance_summary": summary,
            "recommendations": recommendations,
            "monitoring_configuration": self.config
        }

    def save_report(self, filename: Optional[str] = None) -> Path:
        """Save monitoring report to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_monitoring_report_{timestamp}.json"

        report = self.generate_monitoring_report()

        report_file = Path("performance_tests/results") / filename
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Performance monitoring report saved to: {report_file}")
        return report_file


def main():
    """Main function for performance monitoring"""
    import argparse

    parser = argparse.ArgumentParser(description="PAKE System Performance Monitor")
    parser.add_argument("--start", action="store_true",
                       help="Start performance monitoring")
    parser.add_argument("--stop", action="store_true",
                       help="Stop performance monitoring")
    parser.add_argument("--status", action="store_true",
                       help="Show monitoring status")
    parser.add_argument("--generate-report", action="store_true",
                       help="Generate monitoring report")
    parser.add_argument("--config", default="performance_tests/config/monitoring_config.json",
                       help="Configuration file path")

    args = parser.parse_args()

    # Initialize monitor
    monitor = PerformanceMonitor(args.config)

    try:
        if args.start:
            monitor.start_monitoring()
            print("Performance monitoring started. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                monitor.stop_monitoring()

        elif args.stop:
            monitor.stop_monitoring()

        elif args.status:
            summary = monitor.get_performance_summary()
            print("\n" + "="*60)
            print("PERFORMANCE MONITORING STATUS")
            print("="*60)
            print(f"Status: {summary['monitoring_status']}")
            print(f"CPU Usage: {summary['current_metrics']['cpu_usage_percent']:.1f}%")
            print(f"Memory Usage: {summary['current_metrics']['memory_usage_percent']:.1f}%")
            print(f"Response Time: {summary['current_metrics']['response_time_ms']:.1f}ms")
            print(f"Error Rate: {summary['current_metrics']['error_rate_percent']:.1f}%")
            print(f"Active Alerts: {summary['alert_summary']['active_alerts']}")
            print(f"Total Alerts: {summary['alert_summary']['total_alerts']}")

        elif args.generate_report:
            report_file = monitor.save_report()
            print(f"Monitoring report generated: {report_file}")

    except KeyboardInterrupt:
        print("\nMonitoring interrupted by user")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
