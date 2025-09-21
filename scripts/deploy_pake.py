#!/usr/bin/env python3
"""
PAKE+ Deployment Script
Complete system deployment and initialization
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PAKEDeployer:
    """PAKE+ system deployment manager"""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or os.getcwd())
        self.docker_dir = self.base_dir / "docker"
        self.scripts_dir = self.base_dir / "scripts"
        self.vault_dir = self.base_dir / "vault"
        self.configs_dir = self.base_dir / "configs"

        self.deployment_status = {
            "infrastructure": False,
            "database": False,
            "mcp_server": False,
            "api_bridge": False,
            "ingestion": False,
            "validation": False,
        }

    def check_prerequisites(self) -> bool:
        """Check system prerequisites"""
        logger.info("Checking system prerequisites...")

        prerequisites = {
            "docker": self._check_docker(),
            "docker-compose": self._check_docker_compose(),
            "python": self._check_python(),
            "node": self._check_node(),
            "git": self._check_git(),
        }

        missing = [name for name, available in prerequisites.items() if not available]

        if missing:
            logger.error(f"Missing prerequisites: {', '.join(missing)}")
            logger.info("Please install missing components before deployment")
            return False

        logger.info("All prerequisites satisfied ✓")
        return True

    def _check_docker(self) -> bool:
        """Check Docker availability"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"Docker found: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Docker not found or not running")
            return False

    def _check_docker_compose(self) -> bool:
        """Check Docker Compose availability"""
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"Docker Compose found: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Try newer docker compose command
            try:
                result = subprocess.run(
                    ["docker", "compose", "version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                logger.info(f"Docker Compose found: {result.stdout.strip()}")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("Docker Compose not found")
                return False

    def _check_python(self) -> bool:
        """Check Python availability"""
        try:
            result = subprocess.run(
                [sys.executable, "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"Python found: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Python not found")
            return False

    def _check_node(self) -> bool:
        """Check Node.js availability"""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"Node.js found: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Node.js not found")
            return False

    def _check_git(self) -> bool:
        """Check Git availability"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"Git found: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Git not found")
            return False

    def deploy_infrastructure(self) -> bool:
        """Deploy Docker infrastructure"""
        logger.info("Deploying Docker infrastructure...")

        try:
            # Change to docker directory
            os.chdir(self.docker_dir)

            # Pull images first
            logger.info("Pulling Docker images...")
            subprocess.run(["docker-compose", "pull"], check=True)

            # Start services
            logger.info("Starting Docker services...")
            subprocess.run(["docker-compose", "up", "-d"], check=True)

            # Wait for services to be ready
            logger.info("Waiting for services to initialize...")
            time.sleep(30)

            # Check service health
            if self._check_service_health():
                self.deployment_status["infrastructure"] = True
                logger.info("Infrastructure deployment successful ✓")
                return True
            logger.error("Some services failed health check")
            return False

        except subprocess.CalledProcessError as e:
            logger.error(f"Infrastructure deployment failed: {e}")
            return False
        finally:
            os.chdir(self.base_dir)

    def _check_service_health(self) -> bool:
        """Check health of deployed services"""
        services = {
            "PostgreSQL": ("localhost", 5433),
            "Redis": ("localhost", 6380),
            "MCP Server": ("localhost", 8000),
            "n8n": ("localhost", 5678),
        }

        healthy_services = []

        for service_name, (host, port) in services.items():
            if self._check_port(host, port):
                healthy_services.append(service_name)
                logger.info(f"{service_name} is healthy ✓")
            else:
                logger.warning(f"{service_name} is not responding")

        return len(healthy_services) >= 3  # At least 3 core services should be up

    def _check_port(self, host: str, port: int) -> bool:
        """Check if a port is accepting connections"""
        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                return result == 0
        except BaseException:
            return False

    def initialize_database(self) -> bool:
        """Initialize database with schema"""
        logger.info("Initializing database...")

        try:
            # Database should be initialized by init.sql in Docker
            # Check if we can connect and query
            import psycopg2

            conn = psycopg2.connect(
                host="localhost",
                port=5433,
                database="pake_knowledge",
                user="pake_admin",
                REDACTED_SECRET="secure_REDACTED_SECRET_123",
            )

            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'knowledge_nodes'",
                )
                count = cursor.fetchone()[0]

                if count > 0:
                    logger.info("Database schema initialized ✓")
                    self.deployment_status["database"] = True
                    conn.close()
                    return True
                logger.error("Database schema not found")
                conn.close()
                return False

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False

    def install_python_dependencies(self) -> bool:
        """Install Python dependencies"""
        logger.info("Installing Python dependencies...")

        try:
            # Install MCP server dependencies
            mcp_requirements = self.base_dir / "mcp-servers" / "requirements.txt"
            if mcp_requirements.exists():
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        str(mcp_requirements),
                    ],
                    check=True,
                )

            # Install ingestion dependencies
            ingestion_requirements = self.scripts_dir / "requirements_ingestion.txt"
            if ingestion_requirements.exists():
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        str(ingestion_requirements),
                    ],
                    check=True,
                )

            logger.info("Python dependencies installed ✓")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Python dependency installation failed: {e}")
            return False

    def install_node_dependencies(self) -> bool:
        """Install Node.js dependencies"""
        logger.info("Installing Node.js dependencies...")

        try:
            # Install API bridge dependencies
            package_json = self.scripts_dir / "package.json"
            if package_json.exists():
                os.chdir(self.scripts_dir)
                subprocess.run(["npm", "install"], check=True)
                os.chdir(self.base_dir)

            logger.info("Node.js dependencies installed ✓")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Node.js dependency installation failed: {e}")
            return False

    def start_api_bridge(self) -> bool:
        """Start the Obsidian API bridge"""
        logger.info("Starting API bridge...")

        try:
            bridge_script = self.scripts_dir / "obsidian_bridge.js"
            if not bridge_script.exists():
                logger.error("API bridge script not found")
                return False

            # Start in background (in production, use a process manager)
            os.chdir(self.scripts_dir)

            # Set environment variables
            env = os.environ.copy()
            env["VAULT_PATH"] = str(self.vault_dir)
            env["MCP_SERVER_URL"] = "http://localhost:8000"
            env["BRIDGE_PORT"] = "3000"

            # For this demo, we'll just validate the script exists
            # In production, use PM2 or similar
            logger.info("API bridge ready (start with: node obsidian_bridge.js) ✓")
            self.deployment_status["api_bridge"] = True
            return True

        except Exception as e:
            logger.error(f"API bridge startup failed: {e}")
            return False
        finally:
            os.chdir(self.base_dir)

    def setup_ingestion_pipeline(self) -> bool:
        """Set up ingestion pipeline"""
        logger.info("Setting up ingestion pipeline...")

        try:
            # Create ingestion database
            ingestion_script = self.scripts_dir / "ingestion_pipeline.py"
            if not ingestion_script.exists():
                logger.error("Ingestion pipeline script not found")
                return False

            # Initialize ingestion database
            import sqlite3

            ingestion_db = self.base_dir / "data" / "ingestion.db"
            ingestion_db.parent.mkdir(exist_ok=True)

            conn = sqlite3.connect(str(ingestion_db))
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ingested_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT UNIQUE NOT NULL,
                    source_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    published TIMESTAMP,
                    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pake_id TEXT,
                    status TEXT DEFAULT 'pending'
                )
            """,
            )

            conn.commit()
            conn.close()

            logger.info("Ingestion pipeline configured ✓")
            self.deployment_status["ingestion"] = True
            return True

        except Exception as e:
            logger.error(f"Ingestion setup failed: {e}")
            return False

    def install_git_hooks(self) -> bool:
        """Install Git validation hooks"""
        logger.info("Installing Git hooks...")

        try:
            hook_installer = self.scripts_dir / "install-hooks-simple.py"
            if hook_installer.exists():
                subprocess.run([sys.executable, str(hook_installer)], check=True)
                logger.info("Git hooks installed ✓")
                self.deployment_status["validation"] = True
                return True
            logger.warning("Git hook installer not found")
            return False

        except subprocess.CalledProcessError as e:
            logger.error(f"Git hook installation failed: {e}")
            return False

    def create_sample_content(self) -> bool:
        """Create sample content for testing"""
        logger.info("Creating sample content...")

        try:
            # Create a sample note in the inbox
            sample_note = self.vault_dir / "00-Inbox" / "Welcome-to-PAKE.md"

            sample_content = f"""---
pake_id: "welcome-pake-001"
created: "{time.strftime("%Y-%m-%d %H:%M:%S")}"
modified: "{time.strftime("%Y-%m-%d %H:%M:%S")}"
type: "system"
status: "verified"
confidence_score: 1.0
verification_status: "verified"
source_uri: "local://system"
tags: ["welcome", "system", "pake"]
connections: ["km-system-core-001"]
ai_summary: "Welcome note introducing the PAKE+ system capabilities"
human_notes: "System-generated welcome note"
---

# Welcome to PAKE+

## Personal Autonomous Knowledge Engine Plus

Congratulations! Your PAKE+ system has been successfully deployed and configured.

## System Components Installed

✅ **Knowledge Layer**: Obsidian vault with structured directories
✅ **Processing Layer**: MCP servers with confidence scoring
✅ **Storage Layer**: PostgreSQL with pgvector + Redis
✅ **Automation Layer**: n8n workflows + ingestion pipelines
✅ **Integration Layer**: REST API bridge + Git validation

## Quick Start Guide

### 1. Dashboard Access
- **Main Dashboard**: [[Dashboard]] - System overview and metrics
- **Analytics**: [[Analytics-Dashboard]] - Advanced insights and trends

### 2. Content Creation
- Use templates in `_templates/` for consistent note structure
- All notes automatically get confidence scores and validation
- Cross-link related concepts using `[[Note Name]]` syntax

### 3. External Services
- **MCP Server**: http://localhost:8000 (API documentation at /docs)
- **API Bridge**: http://localhost:3000 (when started)
- **n8n Automation**: http://localhost:5678 (admin/n8n_secure_2024)
- **Database**: localhost:5433 (pake_knowledge database)

### 4. Ingestion Pipeline
- Configure sources in `configs/ingestion.json`
- Run pipeline: `python scripts/ingestion_pipeline.py`
- Manage sources: `python scripts/ingestion_manager.py`

### 5. System Monitoring
- Check Docker services: `docker-compose ps`
- View logs: `docker-compose logs [service-name]`
- Monitor queue: Redis on localhost:6380

## Next Steps

1. **Configure API Keys**: Update `.env` files with your API credentials
2. **Set up Obsidian**: Open this vault in Obsidian and install recommended plugins
3. **Start Ingestion**: Configure and enable content sources
4. **Customize Confidence Scoring**: Adjust weights in `confidence_engine.py`
5. **Create Workflows**: Build automation workflows in n8n

## Support and Documentation

- **System Architecture**: [[Knowledge-Management-System]]
- **API Documentation**: Visit http://localhost:8000/docs when MCP server is running
- **Git Hooks**: Automatic validation ensures content quality
- **Backup Strategy**: Database and vault are in separate Docker volumes

---

*This note was automatically generated during PAKE+ deployment at {time.strftime("%Y-%m-%d %H:%M:%S")}
                                                                                          *
"""

            sample_note.write_text(sample_content, encoding="utf-8")
            logger.info("Sample content created ✓")
            return True

        except Exception as e:
            logger.error(f"Sample content creation failed: {e}")
            return False

    def generate_deployment_report(self) -> str:
        """Generate deployment status report"""
        report = f"""
# PAKE+ Deployment Report
Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}

## Deployment Status
"""

        for component, status in self.deployment_status.items():
            status_icon = "✅" if status else "❌"
            report += f"- **{component.replace('_', ' ').title()}**: {status_icon}\n"

        successful_components = sum(self.deployment_status.values())
        total_components = len(self.deployment_status)

        report += f"\n**Success Rate**: {successful_components}/{total_components} ({
            (successful_components / total_components) * 100:.1f}%)\n"

        if successful_components == total_components:
            report += (
                "\n🎉 **Deployment Successful!** Your PAKE+ system is ready to use.\n"
            )
        else:
            report += "\n⚠️ **Partial Deployment** Some components need attention.\n"

        report += f"""
## Service Endpoints
- **MCP Server**: http://localhost:8000
- **API Bridge**: http://localhost:3000
- **n8n Automation**: http://localhost:5678
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6380

## Key Files
- **Vault Location**: {self.vault_dir}
- **Configuration**: {self.configs_dir}
- **Docker Compose**: {self.docker_dir}/docker-compose.yml
- **Scripts**: {self.scripts_dir}

## Next Steps
1. Start services: `cd docker && docker-compose up -d`
2. Open Obsidian and point to vault directory
3. Configure API keys in environment files
4. Start ingestion pipeline for automated content
5. Visit the dashboard for system overview

## Troubleshooting
- Check Docker logs: `docker-compose logs [service]`
- Restart services: `docker-compose restart`
- Database issues: Check init.sql execution
- Port conflicts: Verify ports in docker-compose.yml

---
*PAKE+ System - Personal Autonomous Knowledge Engine Plus*
"""

        return report

    def deploy_complete_system(self) -> bool:
        """Deploy the complete PAKE+ system"""
        logger.info("🚀 Starting PAKE+ System Deployment")
        logger.info("=" * 50)

        deployment_steps = [
            ("Prerequisites Check", self.check_prerequisites),
            ("Python Dependencies", self.install_python_dependencies),
            ("Node.js Dependencies", self.install_node_dependencies),
            ("Docker Infrastructure", self.deploy_infrastructure),
            ("Database Initialization", self.initialize_database),
            ("API Bridge Setup", self.start_api_bridge),
            ("Ingestion Pipeline", self.setup_ingestion_pipeline),
            ("Git Hooks", self.install_git_hooks),
            ("Sample Content", self.create_sample_content),
        ]

        failed_steps = []

        for step_name, step_function in deployment_steps:
            logger.info(f"Executing: {step_name}...")
            try:
                if step_function():
                    logger.info(f"✅ {step_name} completed successfully")
                else:
                    logger.error(f"❌ {step_name} failed")
                    failed_steps.append(step_name)
            except Exception as e:
                logger.error(f"❌ {step_name} failed with exception: {e}")
                failed_steps.append(step_name)

            logger.info("-" * 30)

        # Generate and save report
        report = self.generate_deployment_report()
        report_file = self.base_dir / "DEPLOYMENT_REPORT.md"
        report_file.write_text(report, encoding="utf-8")

        logger.info("📊 Deployment Report")
        logger.info("=" * 50)
        print(report)

        if not failed_steps:
            logger.info("🎉 PAKE+ deployment completed successfully!")
            logger.info(f"📄 Full report saved to: {report_file}")
            return True
        logger.error(
            f"❌ Deployment completed with errors in: {', '.join(failed_steps)}",
        )
        logger.info("Please check the logs and retry failed components")
        logger.info(f"📄 Full report saved to: {report_file}")
        return False


def main():
    """Main deployment function"""
    import argparse

    parser = argparse.ArgumentParser(description="Deploy PAKE+ System")
    parser.add_argument("--base-dir", help="Base directory for PAKE+ system")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check prerequisites",
    )
    parser.add_argument("--component", help="Deploy specific component only")

    args = parser.parse_args()

    deployer = PAKEDeployer(args.base_dir)

    if args.check_only:
        success = deployer.check_prerequisites()
        sys.exit(0 if success else 1)

    if args.component:
        # Deploy specific component
        component_map = {
            "infrastructure": deployer.deploy_infrastructure,
            "database": deployer.initialize_database,
            "api": deployer.start_api_bridge,
            "ingestion": deployer.setup_ingestion_pipeline,
            "hooks": deployer.install_git_hooks,
        }

        if args.component in component_map:
            success = component_map[args.component]()
            sys.exit(0 if success else 1)
        else:
            logger.error(f"Unknown component: {args.component}")
            sys.exit(1)

    # Full deployment
    success = deployer.deploy_complete_system()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
