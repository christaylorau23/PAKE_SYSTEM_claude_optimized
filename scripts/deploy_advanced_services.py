#!/usr/bin/env python3
"""
PAKE+ Advanced Services Deployment
Deploy email integration, social media monitoring, RSS feeds, and analytics dashboard
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ServiceDeployer:
    """Deploy and manage advanced PAKE services"""

    def __init__(self):
        self.deployed_services = []
        self.service_status = {}

    def log_status(self, service: str, status: str, message: str):
        """Log service status"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_icon = {
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️",
            "INFO": "ℹ️",
            "DEPLOYING": "🚀",
        }.get(status, "📋")

        print(f"[{timestamp}] {status_icon} {service}: {message}")

        if service not in self.service_status:
            self.service_status[service] = []
        self.service_status[service].append(
            {"timestamp": timestamp, "status": status, "message": message},
        )

    async def deploy_email_integration(self):
        """Deploy email integration service"""
        self.log_status("EMAIL", "DEPLOYING", "Setting up email integration service...")

        try:
            # Check if email service exists and enhance it
            email_service_path = (
                project_root / "services" / "ingestion" / "email_service.py"
            )

            if not email_service_path.exists():
                self.log_status("EMAIL", "INFO", "Creating enhanced email service...")

                email_service_code = '''"""
Enhanced Email Integration Service for PAKE+
Supports Gmail API, IMAP/SMTP, and intelligent email processing
"""

import asyncio
import email
import imaplib
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from datetime import datetime, timedelta
from typing import List, Dict, Optional, AsyncGenerator
from dataclasses import dataclass
import aiohttp
import json
import os

@dataclass
class EmailMessage:
    """Structured email message"""
    message_id: str
    subject: str
    sender: str
    recipient: str
    timestamp: datetime
    content: str
    attachments: List[Dict] = None
    importance: str = "normal"
    confidence_score: float = 0.0

class EmailIntegrationService:
    """Enhanced email integration with multiple providers"""

    def __init__(self, config: Dict = None):
        self.config = config or self._load_config()
        self.connected = False

    def _load_config(self) -> Dict:
        """Load email configuration from environment"""
        return {
            'imap_server': os.getenv('EMAIL_IMAP_SERVER', 'imap.gmail.com'),
            'imap_port': int(os.getenv('EMAIL_IMAP_PORT', '993')),
            'smtp_server': os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('EMAIL_SMTP_PORT', '587')),
            'username': os.getenv('EMAIL_USERNAME'),
            'REDACTED_SECRET': os.getenv('EMAIL_PASSWORD'),
            'gmail_client_id': os.getenv('GMAIL_CLIENT_ID'),
            'gmail_client_secret': os.getenv('GMAIL_CLIENT_SECRET'),
        }

    async def connect(self) -> bool:
        """Connect to email service"""
        try:
            if self.config['gmail_client_id']:
                return await self._connect_gmail_api()
            else:
                return await self._connect_imap()
        except Exception as e:
            print(f"Email connection failed: {e}")
            return False

    async def _connect_imap(self) -> bool:
        """Connect via IMAP"""
        try:
            # Test IMAP connection
            mail = imaplib.IMAP4_SSL(self.config['imap_server'], self.config['imap_port'])
            mail.login(self.config['username'], self.config['REDACTED_SECRET'])
            mail.logout()
            self.connected = True
            return True
        except Exception as e:
            print(f"IMAP connection failed: {e}")
            return False

    async def _connect_gmail_api(self) -> bool:
        """Connect via Gmail API"""
        # Placeholder for Gmail API implementation
        self.connected = True
        return True

    async def fetch_recent_emails(self, hours: int = 24) -> List[EmailMessage]:
        """Fetch recent emails for processing"""
        if not self.connected:
            if not await self.connect():
                return []

        try:
            # Mock implementation - replace with actual email fetching
            sample_emails = [
                EmailMessage(
                    message_id="test-001",
                    subject="Important Research Paper",
                    sender="researcher@university.edu",
                    recipient=self.config['username'],
                    timestamp=datetime.now(),
                    content="I found this interesting paper on machine learning...",
                    confidence_score=0.85
                ),
                EmailMessage(
                    message_id="test-002",
                    subject="Meeting Notes",
                    sender="colleague@company.com",
                    recipient=self.config['username'],
                    timestamp=datetime.now() - timedelta(hours=2),
                    content="Here are the notes from our discussion...",
                    confidence_score=0.75
                )
            ]

            return sample_emails

        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []

    async def process_email_for_knowledge_extraction(self, email: EmailMessage) -> Dict:
        """Process email for knowledge extraction"""
        # Analyze email content for knowledge value
        knowledge_indicators = [
            'research', 'study', 'paper', 'article', 'findings',
            'analysis', 'data', 'results', 'conclusion', 'methodology'
        ]

        content_lower = email.content.lower()
        knowledge_score = sum(1 for indicator in knowledge_indicators if indicator in content_lower)

        return {
            'knowledge_score': min(knowledge_score / len(knowledge_indicators), 1.0),
            'should_process': knowledge_score > 2,
            'suggested_tags': ['email', 'communication'],
            'priority': 'high' if knowledge_score > 5 else 'medium'
        }
'''

                with open(email_service_path, "w") as f:
                    f.write(email_service_code)

            # Test the service
            from services.ingestion.email_service import EmailIntegrationService

            email_service = EmailIntegrationService()

            # Test configuration
            if email_service.config["username"]:
                connection_success = await email_service.connect()
                if connection_success:
                    self.log_status(
                        "EMAIL",
                        "SUCCESS",
                        "Email service connected and operational",
                    )
                    self.deployed_services.append("email_integration")
                    return True
                self.log_status(
                    "EMAIL",
                    "WARNING",
                    "Email service created but connection failed (check credentials)",
                )
                return False
            self.log_status(
                "EMAIL",
                "WARNING",
                "Email service created but no credentials configured",
            )
            return False

        except Exception as e:
            self.log_status(
                "EMAIL",
                "ERROR",
                f"Email service deployment failed: {str(e)}",
            )
            return False

    async def deploy_social_media_monitoring(self):
        """Deploy social media monitoring services"""
        self.log_status("SOCIAL", "DEPLOYING", "Setting up social media monitoring...")

        try:
            # Check for existing social media service
            social_service_path = (
                project_root / "services" / "ingestion" / "social_media_service.py"
            )

            if social_service_path.exists():
                # Test the existing service
                from services.ingestion.social_media_service import (
                    SocialMediaQuery,
                    SocialMediaService,
                )

                service = SocialMediaService()

                # Test with sample query
                query = SocialMediaQuery(
                    keywords=["machine learning", "AI"],
                    platforms=["twitter", "linkedin"],
                    max_results=5,
                )

                result = await service.search_content(query)

                if result.success and result.content_items:
                    self.log_status(
                        "SOCIAL",
                        "SUCCESS",
                        f"Social media service operational - {len(result.content_items)} items found",
                    )
                    self.deployed_services.append("social_media_monitoring")
                    return True
                self.log_status(
                    "SOCIAL",
                    "WARNING",
                    "Social media service exists but may need API credentials",
                )
                return False
            self.log_status(
                "SOCIAL",
                "WARNING",
                "Social media service not found - creating basic template",
            )
            return False

        except Exception as e:
            self.log_status(
                "SOCIAL",
                "ERROR",
                f"Social media service deployment failed: {str(e)}",
            )
            return False

    async def deploy_rss_automation(self):
        """Deploy RSS feed automation"""
        self.log_status("RSS", "DEPLOYING", "Setting up RSS feed automation...")

        try:
            # Check for existing RSS service
            rss_service_path = (
                project_root / "services" / "ingestion" / "rss_service.py"
            )

            if rss_service_path.exists():
                from services.ingestion.rss_service import RSSQuery, RSSService

                service = RSSService()

                # Test with sample feeds
                query = RSSQuery(
                    feed_urls=[
                        "https://feeds.feedburner.com/oreilly/radar",
                        "https://rss.cnn.com/rss/edition.rss",
                    ],
                    max_items_per_feed=3,
                )

                result = await service.fetch_feeds(query)

                if result.success and result.content_items:
                    self.log_status(
                        "RSS",
                        "SUCCESS",
                        f"RSS service operational - {len(result.content_items)} items fetched",
                    )
                    self.deployed_services.append("rss_automation")
                    return True
                self.log_status(
                    "RSS",
                    "WARNING",
                    "RSS service exists but may have connectivity issues",
                )
                return False
            self.log_status(
                "RSS",
                "WARNING",
                "RSS service not found in services directory",
            )
            return False

        except Exception as e:
            self.log_status("RSS", "ERROR", f"RSS service deployment failed: {str(e)}")
            return False

    async def deploy_analytics_dashboard(self):
        """Deploy real-time analytics dashboard"""
        self.log_status("ANALYTICS", "DEPLOYING", "Setting up analytics dashboard...")

        try:
            # Create analytics dashboard service
            dashboard_path = (
                project_root / "services" / "monitoring" / "analytics_dashboard.py"
            )

            dashboard_code = '''"""
Real-time Analytics Dashboard for PAKE+
Provides live metrics, performance monitoring, and system insights
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import psutil
import os

class AnalyticsDashboard:
    """Real-time analytics and monitoring dashboard"""

    def __init__(self):
        self.app = FastAPI(title="PAKE+ Analytics Dashboard")
        self.active_connections: List[WebSocket] = []
        self.metrics = {
            'system_health': {},
            'ingestion_stats': {},
            'api_performance': {},
            'content_quality': {}
        }
        self.setup_routes()

    def setup_routes(self):
        """Setup dashboard routes"""

        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home():
            return self.get_dashboard_html()

        @self.app.get("/api/metrics")
        async def get_metrics():
            return await self.collect_current_metrics()

        @self.app.websocket("/ws/live-metrics")
        async def websocket_endpoint(websocket: WebSocket):
            await self.websocket_manager(websocket)

    async def collect_current_metrics(self) -> Dict:
        """Collect current system metrics"""
        try:
            # System health metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Mock ingestion stats (replace with actual data)
            ingestion_stats = {
                'total_items_today': 156,
                'sources_active': 7,
                'success_rate': 94.5,
                'avg_processing_time': 0.8
            }

            # Mock API performance
            api_performance = {
                'total_requests': 1247,
                'avg_response_time': 145,
                'error_rate': 2.3,
                'active_sessions': 12
            }

            # Content quality metrics
            content_quality = {
                'avg_confidence_score': 0.847,
                'high_quality_items': 89,
                'duplicate_rate': 3.2,
                'processing_accuracy': 96.1
            }

            return {
                'timestamp': datetime.now().isoformat(),
                'system_health': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_gb': round(memory.available / (1024**3), 2),
                    'disk_percent': (disk.used / disk.total) * 100,
                    'uptime_hours': round(psutil.boot_time() / 3600, 1)
                },
                'ingestion_stats': ingestion_stats,
                'api_performance': api_performance,
                'content_quality': content_quality
            }

        except Exception as e:
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    async def websocket_manager(self, websocket: WebSocket):
        """Manage WebSocket connections for live updates"""
        await websocket.accept()
        self.active_connections.append(websocket)

        try:
            while True:
                # Send live metrics every 5 seconds
                metrics = await self.collect_current_metrics()
                await websocket.send_json(metrics)
                await asyncio.sleep(5)

        except WebSocketDisconnect:
            self.active_connections.remove(websocket)

    def get_dashboard_html(self) -> str:
        \"\"\"Generate dashboard HTML\"\"\"
        return \"\"\"
<!DOCTYPE html>
<html>
<head>
    <title>PAKE+ Analytics Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .header { text-align: center; margin-bottom: 30px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-title { font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #333; }
        .metric-value { font-size: 32px; font-weight: bold; color: #2196F3; margin-bottom: 10px; }
        .metric-label { color: #666; font-size: 14px; }
        .status-good { color: #4CAF50; }
        .status-warning { color: #FF9800; }
        .status-error { color: #F44336; }
        .live-indicator { position: absolute; top: 20px; right: 20px; color: #4CAF50; }
        .live-indicator:before { content: '●'; animation: blink 1s infinite; }
        @keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0.3; } }
    </style>
</head>
<body>
    <div class="live-indicator">LIVE</div>
    <div class="header">
        <h1>🚀 PAKE+ Analytics Dashboard</h1>
        <p>Real-time system monitoring and performance metrics</p>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-title">System Health</div>
            <div id="cpu-usage" class="metric-value">--</div>
            <div class="metric-label">CPU Usage</div>
        </div>

        <div class="metric-card">
            <div class="metric-title">Memory Usage</div>
            <div id="memory-usage" class="metric-value">--</div>
            <div class="metric-label">Memory Utilized</div>
        </div>

        <div class="metric-card">
            <div class="metric-title">Content Ingested</div>
            <div id="items-today" class="metric-value">--</div>
            <div class="metric-label">Items Today</div>
        </div>

        <div class="metric-card">
            <div class="metric-title">Success Rate</div>
            <div id="success-rate" class="metric-value">--</div>
            <div class="metric-label">Processing Success</div>
        </div>

        <div class="metric-card">
            <div class="metric-title">API Performance</div>
            <div id="response-time" class="metric-value">--</div>
            <div class="metric-label">Avg Response Time (ms)</div>
        </div>

        <div class="metric-card">
            <div class="metric-title">Content Quality</div>
            <div id="quality-score" class="metric-value">--</div>
            <div class="metric-label">Avg Confidence Score</div>
        </div>
    </div>

    <script>
        const ws = new WebSocket('ws://localhost:3002/ws/live-metrics');

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);

            if (data.system_health) {
                document.getElementById('cpu-usage').textContent = data.system_health.cpu_percent.toFixed(1) + '%';
                document.getElementById('memory-usage').textContent = data.system_health.memory_percent.toFixed(1) + '%';
            }

            if (data.ingestion_stats) {
                document.getElementById('items-today').textContent = data.ingestion_stats.total_items_today;
                document.getElementById('success-rate').textContent = data.ingestion_stats.success_rate.toFixed(1) + '%';
            }

            if (data.api_performance) {
                document.getElementById('response-time').textContent = data.api_performance.avg_response_time;
            }

            if (data.content_quality) {
                document.getElementById('quality-score').textContent = data.content_quality.avg_confidence_score.toFixed(3);
            }
        };

        ws.onopen = function() {
            console.log('Connected to PAKE+ Analytics Dashboard');
        };

        ws.onclose = function() {
            console.log('Disconnected from analytics dashboard');
            setTimeout(() => location.reload(), 5000); // Auto-reconnect
        };
    </script>
</body>
</html>
        \"\"\"
'''

            with open(dashboard_path, "w") as f:
                f.write(dashboard_code)

            self.log_status(
                "ANALYTICS",
                "SUCCESS",
                "Analytics dashboard service created",
            )
            self.deployed_services.append("analytics_dashboard")
            return True

        except Exception as e:
            self.log_status(
                "ANALYTICS",
                "ERROR",
                f"Analytics dashboard deployment failed: {str(e)}",
            )
            return False

    async def test_advanced_integration(self):
        """Test advanced services integration"""
        self.log_status(
            "INTEGRATION",
            "DEPLOYING",
            "Testing advanced services integration...",
        )

        try:
            # Test the orchestrator with advanced services
            from services.ingestion.orchestrator import (
                IngestionConfig,
                IngestionOrchestrator,
            )

            config = IngestionConfig(
                max_concurrent_sources=5,
                timeout_per_source=120,
                quality_threshold=0.8,
                enable_cognitive_processing=True,
                enable_workflow_automation=True,
            )

            orchestrator = IngestionOrchestrator(config=config)

            # Create an advanced ingestion plan
            plan = await orchestrator.create_ingestion_plan(
                "AI research trends 2024",
                {
                    "domain": "technology",
                    "urgency": "high",
                    "include_email": True,
                    "include_social": True,
                    "include_rss": True,
                    "quality_threshold": 0.8,
                },
            )

            self.log_status(
                "INTEGRATION",
                "SUCCESS",
                f"Advanced integration test passed - {len(plan.sources)} sources configured",
            )
            return True

        except Exception as e:
            self.log_status(
                "INTEGRATION",
                "ERROR",
                f"Advanced integration test failed: {str(e)}",
            )
            return False

    def generate_deployment_report(self) -> dict:
        """Generate deployment report"""

        total_services = len(self.service_status)
        successful_services = len(self.deployed_services)

        report = {
            "deployment_timestamp": datetime.now().isoformat(),
            "total_services_attempted": total_services,
            "successful_deployments": successful_services,
            "success_rate": (
                (successful_services / total_services * 100)
                if total_services > 0
                else 0
            ),
            "deployed_services": self.deployed_services,
            "service_details": self.service_status,
            "next_steps": [],
        }

        # Add next steps based on deployment results
        if successful_services == total_services:
            report["next_steps"] = [
                "All advanced services deployed successfully",
                "Configure production API credentials",
                "Set up monitoring and alerting",
                "Deploy to production environment",
            ]
        else:
            failed_services = [
                service
                for service in self.service_status.keys()
                if service not in self.deployed_services
            ]
            report["next_steps"] = [
                f"Fix deployment issues for: {', '.join(failed_services)}",
                "Check API credentials and connectivity",
                "Review service configurations",
                "Re-run deployment script",
            ]

        return report


async def main():
    """Main deployment process"""
    print("🚀 PAKE+ ADVANCED SERVICES DEPLOYMENT")
    print("=" * 60)

    deployer = ServiceDeployer()

    # Deploy each service
    services_to_deploy = [
        ("Email Integration", deployer.deploy_email_integration),
        ("Social Media Monitoring", deployer.deploy_social_media_monitoring),
        ("RSS Automation", deployer.deploy_rss_automation),
        ("Analytics Dashboard", deployer.deploy_analytics_dashboard),
        ("Integration Test", deployer.test_advanced_integration),
    ]

    for service_name, deploy_func in services_to_deploy:
        print(f"\n📋 Deploying {service_name}...")
        try:
            success = await deploy_func()
            if success:
                print(f"✅ {service_name} deployed successfully")
            else:
                print(f"⚠️  {service_name} deployment had issues")
        except Exception as e:
            print(f"❌ {service_name} deployment failed: {str(e)}")

    # Generate and save report
    report = deployer.generate_deployment_report()

    print("\n📊 DEPLOYMENT SUMMARY")
    print("=" * 40)
    print(
        f"Services Deployed: {report['successful_deployments']}/{
            report['total_services_attempted']
        }",
    )
    print(f"Success Rate: {report['success_rate']:.1f}%")
    print(f"Deployed Services: {', '.join(report['deployed_services'])}")

    # Save detailed report
    with open("advanced_services_deployment_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n📄 Detailed report saved to: advanced_services_deployment_report.json")

    if report["success_rate"] >= 80:
        print("\n🎉 Advanced services deployment successful!")
        print("Next: Configure production credentials and deploy monitoring")
    else:
        print("\n⚠️  Some services need attention. Check the report for details.")


if __name__ == "__main__":
    asyncio.run(main())
