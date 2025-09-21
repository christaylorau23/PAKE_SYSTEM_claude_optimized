#!/usr/bin/env python3
"""
PAKE+ Master Orchestrator
Unified deployment, service management, and error recovery system
Addresses all critical issues identified in system analysis
"""

import asyncio
import logging
import os
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class ServiceStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ServiceConfig:
    name: str
    port: int
    host: str = "localhost"
    dependencies: list[str] = None
    start_command: str = None
    health_endpoint: str = None
    required: bool = True
    timeout: int = 60
    restart_on_failure: bool = True


class PAKEMasterOrchestrator:
    """Unified PAKE+ system orchestrator"""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or os.getcwd())
        self.docker_dir = self.base_dir / "docker"
        self.scripts_dir = self.base_dir / "scripts"
        self.vault_dir = self.base_dir / "vault"
        self.logs_dir = self.base_dir / "logs"
        self.data_dir = self.base_dir / "data"

        # Ensure directories exist
        for directory in [self.logs_dir, self.data_dir]:
            directory.mkdir(exist_ok=True)

        # Setup logging
        self.setup_logging()

        # Service configurations
        self.services = self.load_service_configs()

        # Status tracking
        self.deployment_status = {}
        self.service_processes = {}
        self.health_check_failures = {}

        # Graceful shutdown handling
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def setup_logging(self):
        """Setup comprehensive logging system"""
        log_file = (
            self.logs_dir
            / f"master_orchestrator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Setup file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)

        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Setup root logger
        self.logger = logging.getLogger("PAKEOrchestrator")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info(f"PAKE Master Orchestrator initialized - Log file: {log_file}")

    def load_service_configs(self) -> dict[str, ServiceConfig]:
        """Load service configurations"""
        return {
            "postgres": ServiceConfig(
                name="PostgreSQL",
                port=5432,
                dependencies=[],
                health_endpoint="tcp",
                required=True,
                timeout=120,
            ),
            "redis": ServiceConfig(
                name="Redis",
                port=6379,
                dependencies=[],
                health_endpoint="tcp",
                required=True,
                timeout=60,
            ),
            "mcp_server": ServiceConfig(
                name="MCP Server",
                port=8000,
                dependencies=["postgres", "redis"],
                health_endpoint="http://localhost:8000/health",
                required=True,
                timeout=90,
            ),
            "n8n": ServiceConfig(
                name="n8n Automation",
                port=5678,
                dependencies=["postgres"],
                health_endpoint="http://localhost:5678",
                required=False,
                timeout=120,
            ),
            "api_bridge": ServiceConfig(
                name="API Bridge",
                port=3000,
                dependencies=["mcp_server"],
                start_command="node obsidian_bridge.js",
                health_endpoint="http://localhost:3000/health",
                required=True,
                timeout=60,
            ),
            "frontend": ServiceConfig(
                name="Frontend",
                port=3001,
                dependencies=[],
                start_command="npm run dev",
                health_endpoint="http://localhost:3001",
                required=False,
                timeout=90,
            ),
            "nginx": ServiceConfig(
                name="Nginx Reverse Proxy",
                port=80,
                dependencies=["mcp_server", "api_bridge"],
                health_endpoint="http://localhost",
                required=False,
                timeout=30,
            ),
        }

    async def check_prerequisites(self) -> bool:
        """Comprehensive prerequisite checking"""
        self.logger.info("🔍 Checking system prerequisites...")

        prerequisites = {
            "docker": self._check_docker(),
            "docker-compose": self._check_docker_compose(),
            "python": self._check_python(),
            "node": self._check_node(),
            "git": self._check_git(),
            "npm": self._check_npm(),
        }

        missing = [name for name, available in prerequisites.items() if not available]

        if missing:
            self.logger.error(f"❌ Missing prerequisites: {', '.join(missing)}")
            self.logger.info("Please install missing components:")
            for prereq in missing:
                self._show_installation_instructions(prereq)
            return False

        # Check for required files
        required_files = [
            self.docker_dir / "docker-compose.yml",
            self.base_dir / ".env.example",
        ]

        for file_path in required_files:
            if not file_path.exists():
                self.logger.error(f"❌ Required file missing: {file_path}")
                return False

        self.logger.info("✅ All prerequisites satisfied")
        return True

    def _check_docker(self) -> bool:
        """Check Docker availability"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.logger.info(f"✅ Docker: {result.stdout.strip()}")
                return True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            pass

        self.logger.warning("❌ Docker not found or not running")
        return False

    def _check_docker_compose(self) -> bool:
        """Check Docker Compose availability"""
        # Try both docker-compose and docker compose
        for cmd in [["docker-compose", "--version"], ["docker", "compose", "version"]]:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self.logger.info(f"✅ Docker Compose: {result.stdout.strip()}")
                    return True
            except (
                subprocess.CalledProcessError,
                FileNotFoundError,
                subprocess.TimeoutExpired,
            ):
                continue

        self.logger.warning("❌ Docker Compose not found")
        return False

    def _check_python(self) -> bool:
        """Check Python availability"""
        try:
            result = subprocess.run(
                [sys.executable, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.logger.info(f"✅ Python: {result.stdout.strip()}")
                return True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            pass

        self.logger.warning("❌ Python not found")
        return False

    def _check_node(self) -> bool:
        """Check Node.js availability"""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.logger.info(f"✅ Node.js: {result.stdout.strip()}")
                return True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            pass

        self.logger.warning("❌ Node.js not found")
        return False

    def _check_npm(self) -> bool:
        """Check npm availability"""
        try:
            result = subprocess.run(
                ["npm", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.logger.info(f"✅ npm: {result.stdout.strip()}")
                return True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            pass

        self.logger.warning("❌ npm not found")
        return False

    def _check_git(self) -> bool:
        """Check Git availability"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.logger.info(f"✅ Git: {result.stdout.strip()}")
                return True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            pass

        self.logger.warning("❌ Git not found")
        return False

    def _show_installation_instructions(self, prerequisite: str):
        """Show installation instructions for missing prerequisites"""
        instructions = {
            "docker": "Install Docker Desktop: https://docs.docker.com/get-docker/",
            "docker-compose": "Docker Compose included with Docker Desktop",
            "python": "Install Python 3.9+: https://python.org/downloads/",
            "node": "Install Node.js 18+: https://nodejs.org/",
            "git": "Install Git: https://git-scm.com/downloads",
            "npm": "npm comes with Node.js installation",
        }

        if prerequisite in instructions:
            self.logger.info(f"  → {instructions[prerequisite]}")

    async def setup_environment(self) -> bool:
        """Setup and validate environment"""
        self.logger.info("🔧 Setting up environment...")

        try:
            # Create .env file if it doesn't exist
            env_file = self.base_dir / ".env"
            env_example = self.base_dir / ".env.example"

            if not env_file.exists() and env_example.exists():
                self.logger.info("Creating .env file from template...")
                shutil.copy2(env_example, env_file)
                self.logger.warning("⚠️  Please edit .env file with your actual values")

            # Create required directories
            directories = [
                self.vault_dir,
                self.vault_dir / "00-Inbox",
                self.vault_dir / "01-Sources",
                self.vault_dir / "02-Processing",
                self.vault_dir / "03-Knowledge",
                self.vault_dir / "04-Projects",
                self.vault_dir / "_templates",
                self.data_dir,
                self.logs_dir,
            ]

            for directory in directories:
                directory.mkdir(exist_ok=True, parents=True)

            self.logger.info("✅ Environment setup completed")
            return True

        except Exception as e:
            self.logger.error(f"❌ Environment setup failed: {e}")
            return False

    async def install_dependencies(self) -> bool:
        """Install all dependencies"""
        self.logger.info("📦 Installing dependencies...")

        tasks = []

        # Install Python dependencies
        tasks.append(self._install_python_dependencies())

        # Install Node.js dependencies
        tasks.append(self._install_node_dependencies())

        # Execute all installations
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success = all(not isinstance(r, Exception) and r for r in results)

        if success:
            self.logger.info("✅ All dependencies installed")
        else:
            self.logger.error("❌ Some dependency installations failed")

        return success

    async def _install_python_dependencies(self) -> bool:
        """Install Python dependencies"""
        try:
            # Install MCP server dependencies
            mcp_requirements = self.base_dir / "mcp-servers" / "requirements.txt"
            if mcp_requirements.exists():
                await self._run_command_async(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        str(mcp_requirements),
                    ],
                )

            # Install ingestion dependencies
            ingestion_requirements = self.scripts_dir / "requirements_ingestion.txt"
            if ingestion_requirements.exists():
                await self._run_command_async(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        str(ingestion_requirements),
                    ],
                )

            # Install general requirements
            general_requirements = self.base_dir / "requirements.txt"
            if general_requirements.exists():
                await self._run_command_async(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        str(general_requirements),
                    ],
                )

            self.logger.info("✅ Python dependencies installed")
            return True

        except Exception as e:
            self.logger.error(f"❌ Python dependency installation failed: {e}")
            return False

    async def _install_node_dependencies(self) -> bool:
        """Install Node.js dependencies"""
        try:
            # Install scripts dependencies
            package_json = self.scripts_dir / "package.json"
            if package_json.exists():
                await self._run_command_async(["npm", "install"], cwd=self.scripts_dir)

            # Install frontend dependencies
            frontend_package = self.base_dir / "frontend" / "package.json"
            if frontend_package.exists():
                await self._run_command_async(
                    ["npm", "install"],
                    cwd=self.base_dir / "frontend",
                )

            self.logger.info("✅ Node.js dependencies installed")
            return True

        except Exception as e:
            self.logger.error(f"❌ Node.js dependency installation failed: {e}")
            return False

    async def _run_command_async(
        self,
        command: list[str],
        cwd: Path = None,
        timeout: int = 300,
    ) -> subprocess.CompletedProcess:
        """Run command asynchronously with timeout"""
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd or self.base_dir,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode,
                    command,
                    stdout,
                    stderr,
                )

            return subprocess.CompletedProcess(command, 0, stdout, stderr)

        except TimeoutError:
            process.terminate()
            await process.wait()
            raise subprocess.TimeoutExpired(command, timeout)

    async def deploy_infrastructure(self) -> bool:
        """Deploy Docker infrastructure with proper error handling"""
        self.logger.info("🐳 Deploying Docker infrastructure...")

        try:
            # Ensure Docker is running
            if not await self._ensure_docker_running():
                return False

            # Change to docker directory
            original_dir = os.getcwd()
            os.chdir(self.docker_dir)

            try:
                # Stop any running services first
                self.logger.info("Stopping existing services...")
                await self._run_command_async(["docker-compose", "down"], timeout=60)

                # Pull latest images
                self.logger.info("Pulling Docker images...")
                await self._run_command_async(["docker-compose", "pull"], timeout=300)

                # Start services
                self.logger.info("Starting Docker services...")
                await self._run_command_async(
                    ["docker-compose", "up", "-d"],
                    timeout=180,
                )

                # Wait for services to stabilize
                self.logger.info("Waiting for services to initialize...")
                await asyncio.sleep(30)

                # Check service health
                if await self._verify_docker_services():
                    self.deployment_status["infrastructure"] = True
                    self.logger.info("✅ Infrastructure deployment successful")
                    return True
                self.logger.error("❌ Some services failed health check")
                return False

            finally:
                os.chdir(original_dir)

        except Exception as e:
            self.logger.error(f"❌ Infrastructure deployment failed: {e}")
            return False

    async def _ensure_docker_running(self) -> bool:
        """Ensure Docker daemon is running"""
        try:
            await self._run_command_async(["docker", "info"], timeout=10)
            return True
        except Exception:
            self.logger.error(
                "❌ Docker daemon not running. Please start Docker Desktop.",
            )
            return False

    async def _verify_docker_services(self) -> bool:
        """Verify Docker services are healthy"""
        docker_services = ["postgres", "redis", "mcp_server"]
        healthy_services = 0

        for service in docker_services:
            if service in self.services:
                config = self.services[service]
                if await self._check_service_health(service, config):
                    healthy_services += 1
                    self.logger.info(f"✅ {config.name} is healthy")
                else:
                    self.logger.warning(f"❌ {config.name} health check failed")

        return healthy_services >= len(docker_services) - 1  # Allow one service to fail

    async def _check_service_health(
        self,
        service_name: str,
        config: ServiceConfig,
    ) -> bool:
        """Check health of a specific service"""
        try:
            if config.health_endpoint == "tcp":
                return await self._check_tcp_health(config.host, config.port)
            if config.health_endpoint and config.health_endpoint.startswith("http"):
                return await self._check_http_health(config.health_endpoint)
            return await self._check_tcp_health(config.host, config.port)

        except Exception as e:
            self.logger.debug(f"Health check failed for {service_name}: {e}")
            return False

    async def _check_tcp_health(self, host: str, port: int) -> bool:
        """Check TCP connection health"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except BaseException:
            return False

    async def _check_http_health(self, url: str) -> bool:
        """Check HTTP endpoint health"""
        try:
            import aiohttp

            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response,
            ):
                return response.status < 400

        except ImportError:
            # Fallback to subprocess curl
            try:
                await self._run_command_async(["curl", "-f", "-s", url], timeout=5)
                return True
            except BaseException:
                return False
        except BaseException:
            return False

    async def start_services(self) -> bool:
        """Start all services in dependency order"""
        self.logger.info("🚀 Starting all services...")

        # Get startup order based on dependencies
        startup_order = self._calculate_startup_order()

        for service_name in startup_order:
            config = self.services[service_name]

            # Skip Docker services (already started)
            if service_name in ["postgres", "redis", "mcp_server", "n8n", "nginx"]:
                continue

            if config.start_command:
                success = await self._start_individual_service(service_name, config)
                if not success and config.required:
                    self.logger.error(
                        f"❌ Required service {config.name} failed to start",
                    )
                    return False

            await asyncio.sleep(2)  # Brief delay between services

        self.logger.info("✅ All services started successfully")
        return True

    def _calculate_startup_order(self) -> list[str]:
        """Calculate service startup order based on dependencies"""
        ordered = []
        remaining = set(self.services.keys())

        while remaining:
            ready = []

            for service_name in remaining:
                config = self.services[service_name]
                deps = config.dependencies or []

                if all(dep in ordered for dep in deps):
                    ready.append(service_name)

            if not ready:
                # Break circular dependencies
                ready = list(remaining)

            for service_name in ready:
                ordered.append(service_name)
                remaining.remove(service_name)

        return ordered

    async def _start_individual_service(
        self,
        service_name: str,
        config: ServiceConfig,
    ) -> bool:
        """Start an individual service"""
        self.logger.info(f"Starting {config.name}...")

        try:
            # Set up environment
            env = os.environ.copy()
            env.update(
                {
                    "VAULT_PATH": str(self.vault_dir),
                    "MCP_SERVER_URL": "http://localhost:8000",
                    "API_BRIDGE_URL": "http://localhost:3000",
                    "NODE_ENV": "development",
                },
            )

            # Determine working directory
            if service_name == "api_bridge":
                cwd = self.scripts_dir
            elif service_name == "frontend":
                cwd = self.base_dir / "frontend"
            else:
                cwd = self.base_dir

            # Start the service
            command = config.start_command.split()
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            self.service_processes[service_name] = process

            # Wait for service to become healthy
            for attempt in range(config.timeout // 5):
                if await self._check_service_health(service_name, config):
                    self.logger.info(f"✅ {config.name} started successfully")
                    return True

                await asyncio.sleep(5)

            self.logger.error(f"❌ {config.name} failed to become healthy")
            return False

        except Exception as e:
            self.logger.error(f"❌ Failed to start {config.name}: {e}")
            return False

    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        self.logger.info("🛑 Shutdown signal received, stopping services...")

        asyncio.create_task(self.stop_all_services())

    async def stop_all_services(self):
        """Stop all services gracefully"""
        # Stop managed processes
        for service_name, process in self.service_processes.items():
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=10)
                self.logger.info(f"✅ Stopped {service_name}")
            except TimeoutError:
                process.kill()
                self.logger.info(f"🔥 Force killed {service_name}")
            except Exception as e:
                self.logger.error(f"❌ Error stopping {service_name}: {e}")

        # Stop Docker services
        try:
            original_dir = os.getcwd()
            os.chdir(self.docker_dir)

            await self._run_command_async(["docker-compose", "down"], timeout=60)
            self.logger.info("✅ Docker services stopped")

            os.chdir(original_dir)

        except Exception as e:
            self.logger.error(f"❌ Error stopping Docker services: {e}")

    async def full_deployment(self) -> bool:
        """Execute full PAKE+ deployment"""
        self.logger.info("🚀 Starting PAKE+ Full Deployment")
        self.logger.info("=" * 60)

        deployment_steps = [
            ("Prerequisites Check", self.check_prerequisites),
            ("Environment Setup", self.setup_environment),
            ("Dependencies Installation", self.install_dependencies),
            ("Docker Infrastructure", self.deploy_infrastructure),
            ("Service Startup", self.start_services),
        ]

        failed_steps = []

        for step_name, step_function in deployment_steps:
            self.logger.info(f"📋 {step_name}...")

            try:
                success = await step_function()

                if success:
                    self.logger.info(f"✅ {step_name} completed")
                else:
                    self.logger.error(f"❌ {step_name} failed")
                    failed_steps.append(step_name)

            except Exception as e:
                self.logger.error(f"❌ {step_name} failed with exception: {e}")
                failed_steps.append(step_name)

            self.logger.info("-" * 40)

        # Generate deployment report
        await self._generate_deployment_report(failed_steps)

        if not failed_steps:
            self.logger.info("🎉 PAKE+ deployment completed successfully!")
            return True
        self.logger.error(f"❌ Deployment failed at: {', '.join(failed_steps)}")
        return False

    async def _generate_deployment_report(self, failed_steps: list[str]):
        """Generate comprehensive deployment report"""
        report_content = f"""# PAKE+ Deployment Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Status Summary
{"✅ SUCCESS" if not failed_steps else "❌ PARTIAL FAILURE"}

## Step Results
"""

        all_steps = [
            "Prerequisites Check",
            "Environment Setup",
            "Dependencies Installation",
            "Docker Infrastructure",
            "Service Startup",
        ]

        for step in all_steps:
            status = "❌ FAILED" if step in failed_steps else "✅ SUCCESS"
            report_content += f"- **{step}**: {status}\n"

        if failed_steps:
            report_content += "\n## Failed Steps\n"
            for step in failed_steps:
                report_content += f"- {step}\n"

            report_content += "\n## Troubleshooting\n"
            report_content += "1. Check logs in the logs/ directory\n"
            report_content += "2. Verify Docker Desktop is running\n"
            report_content += "3. Ensure all prerequisites are installed\n"
            report_content += "4. Check .env file configuration\n"

        report_content += """
## Service Endpoints
- **MCP Server**: http://localhost:8000
- **API Bridge**: http://localhost:3000
- **n8n Automation**: http://localhost:5678
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Frontend**: http://localhost:3001

## Next Steps
1. Verify service health: Check endpoints above
2. Review logs for any errors
3. Test core functionality
4. Configure API keys in .env file

---
*Generated by PAKE+ Master Orchestrator*
"""

        report_file = self.base_dir / "DEPLOYMENT_REPORT.md"
        report_file.write_text(report_content, encoding="utf-8")

        self.logger.info(f"📊 Deployment report saved: {report_file}")


async def main():
    """Main orchestrator entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="PAKE+ Master Orchestrator")
    parser.add_argument(
        "command",
        choices=["deploy", "start", "stop", "status", "check"],
        help="Command to execute",
    )
    parser.add_argument("--base-dir", help="Base directory for PAKE+ system")
    parser.add_argument("--service", help="Specific service to operate on")

    args = parser.parse_args()

    orchestrator = PAKEMasterOrchestrator(args.base_dir)

    if args.command == "deploy":
        success = await orchestrator.full_deployment()
        sys.exit(0 if success else 1)

    elif args.command == "start":
        if args.service:
            # Start specific service
            if args.service in orchestrator.services:
                config = orchestrator.services[args.service]
                success = await orchestrator._start_individual_service(
                    args.service,
                    config,
                )
                sys.exit(0 if success else 1)
            else:
                orchestrator.logger.error(f"Unknown service: {args.service}")
                sys.exit(1)
        else:
            # Start all services
            success = await orchestrator.start_services()
            sys.exit(0 if success else 1)

    elif args.command == "stop":
        await orchestrator.stop_all_services()
        sys.exit(0)

    elif args.command == "status":
        # Check all service statuses
        for service_name, config in orchestrator.services.items():
            health = await orchestrator._check_service_health(service_name, config)
            status = "🟢 HEALTHY" if health else "🔴 UNHEALTHY"
            print(f"{config.name}: {status}")
        sys.exit(0)

    elif args.command == "check":
        success = await orchestrator.check_prerequisites()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)
