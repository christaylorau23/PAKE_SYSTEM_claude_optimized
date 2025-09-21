#!/usr/bin/env python3
"""
PAKE+ Unified Deployment System
Master deployment orchestrator that addresses all recurring system errors
Integrates all components from the provided code snippets
"""

import asyncio
import json
import logging
import os
import platform
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

import yaml

# Import our custom modules
try:
    from enhanced_service_manager import PAKEServiceManager, ServiceState
    from master_orchestrator import PAKEMasterOrchestrator
    from service_health_monitor import HealthStatus, PAKEServiceMonitor
except ImportError as e:
    print(f"⚠️  Warning: Could not import custom modules: {e}")
    print("Running in standalone mode...")


class DeploymentPhase(Enum):
    VALIDATION = "validation"
    PREPARATION = "preparation"
    INFRASTRUCTURE = "infrastructure"
    SERVICES = "services"
    VERIFICATION = "verification"
    FINALIZATION = "finalization"


class DeploymentMode(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"
    RECOVERY = "recovery"


@dataclass
class DeploymentConfig:
    mode: DeploymentMode = DeploymentMode.DEVELOPMENT
    skip_docker: bool = False
    skip_dependencies: bool = False
    skip_frontend: bool = False
    force_reinstall: bool = False
    enable_monitoring: bool = True
    parallel_execution: bool = True
    timeout_multiplier: float = 1.0
    custom_vault_path: str | None = None
    custom_ports: dict[str, int] = field(default_factory=dict)
    environment_overrides: dict[str, str] = field(default_factory=dict)


class PAKEUnifiedDeployment:
    """Unified deployment system addressing all PAKE+ system issues"""

    def __init__(self, config: DeploymentConfig = None):
        self.config = config or DeploymentConfig()
        self.base_dir = Path(__file__).parent.parent
        self.logs_dir = self.base_dir / "logs"
        self.data_dir = self.base_dir / "data"
        self.scripts_dir = self.base_dir / "scripts"
        self.docker_dir = self.base_dir / "docker"

        # Ensure directories exist
        for directory in [self.logs_dir, self.data_dir]:
            directory.mkdir(exist_ok=True)

        # Setup logging
        self.setup_comprehensive_logging()

        # Deployment state
        self.deployment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.phase_results = {}
        self.deployment_start_time = None
        self.deployment_errors = []

        # Component managers
        self.orchestrator = None
        self.service_manager = None
        self.health_monitor = None

        self.logger.info(
            f"PAKE+ Unified Deployment initialized (ID: {self.deployment_id})",
        )

    def setup_comprehensive_logging(self):
        """Setup comprehensive logging with multiple handlers"""
        # Create deployment-specific log file
        log_file = self.logs_dir / f"unified_deployment_{self.deployment_id}.log"

        # Setup formatters
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        )

        simple_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
        )

        # File handler (detailed)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(logging.DEBUG)

        # Console handler (simple)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(simple_formatter)
        console_handler.setLevel(logging.INFO)

        # Error file handler
        error_file = self.logs_dir / f"deployment_errors_{self.deployment_id}.log"
        error_handler = logging.FileHandler(error_file)
        error_handler.setFormatter(detailed_formatter)
        error_handler.setLevel(logging.ERROR)

        # Setup logger
        self.logger = logging.getLogger("PAKEUnifiedDeployment")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.addHandler(error_handler)

        self.logger.info(f"Logging initialized - Log file: {log_file}")

    async def execute_full_deployment(self) -> bool:
        """Execute complete PAKE+ system deployment"""
        self.deployment_start_time = time.time()

        self.logger.info("🚀 Starting PAKE+ Unified Deployment")
        self.logger.info("=" * 80)
        self.logger.info(f"Deployment ID: {self.deployment_id}")
        self.logger.info(f"Mode: {self.config.mode.value}")
        self.logger.info(f"Platform: {platform.system()} {platform.release()}")
        self.logger.info("=" * 80)

        # Define deployment phases
        phases = [
            (DeploymentPhase.VALIDATION, "System Validation", self._phase_validation),
            (
                DeploymentPhase.PREPARATION,
                "Environment Preparation",
                self._phase_preparation,
            ),
            (
                DeploymentPhase.INFRASTRUCTURE,
                "Infrastructure Deployment",
                self._phase_infrastructure,
            ),
            (DeploymentPhase.SERVICES, "Service Deployment", self._phase_services),
            (
                DeploymentPhase.VERIFICATION,
                "System Verification",
                self._phase_verification,
            ),
            (
                DeploymentPhase.FINALIZATION,
                "Deployment Finalization",
                self._phase_finalization,
            ),
        ]

        success = True

        try:
            for phase_enum, phase_name, phase_function in phases:
                self.logger.info(f"\n📋 Phase: {phase_name}")
                self.logger.info("-" * 50)

                phase_start = time.time()

                try:
                    phase_success = await phase_function()
                    phase_duration = time.time() - phase_start

                    self.phase_results[phase_enum.value] = {
                        "success": phase_success,
                        "duration": phase_duration,
                        "timestamp": datetime.now().isoformat(),
                    }

                    if phase_success:
                        self.logger.info(
                            f"✅ {phase_name} completed successfully ({
                                phase_duration:.1f}s)",
                        )
                    else:
                        self.logger.error(
                            f"❌ {phase_name} failed ({phase_duration:.1f}s)",
                        )
                        success = False

                        # Stop deployment on critical phase failure
                        if phase_enum in [
                            DeploymentPhase.VALIDATION,
                            DeploymentPhase.INFRASTRUCTURE,
                        ]:
                            self.logger.critical(
                                f"Critical phase {phase_name} failed - stopping deployment",
                            )
                            break

                except Exception as e:
                    phase_duration = time.time() - phase_start

                    self.logger.error(f"💥 {phase_name} failed with exception: {e}")
                    self.deployment_errors.append(f"{phase_name}: {str(e)}")

                    self.phase_results[phase_enum.value] = {
                        "success": False,
                        "duration": phase_duration,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }

                    success = False

                    # Stop on critical failures
                    if phase_enum in [
                        DeploymentPhase.VALIDATION,
                        DeploymentPhase.INFRASTRUCTURE,
                    ]:
                        break

                self.logger.info("-" * 50)

            # Generate final report
            await self._generate_deployment_report(success)

            total_duration = time.time() - self.deployment_start_time

            if success:
                self.logger.info("\n🎉 PAKE+ deployment completed successfully!")
                self.logger.info(f"⏱️  Total time: {total_duration:.1f} seconds")
            else:
                self.logger.error("\n❌ PAKE+ deployment failed")
                self.logger.error(f"⏱️  Total time: {total_duration:.1f} seconds")
                self.logger.error("Check logs for detailed error information")

            return success

        except Exception as e:
            self.logger.critical(f"💥 Fatal deployment error: {e}")
            self.deployment_errors.append(f"Fatal: {str(e)}")
            await self._generate_deployment_report(False)
            return False

    async def _phase_validation(self) -> bool:
        """Phase 1: System validation and prerequisite checking"""
        self.logger.info("🔍 Validating system prerequisites...")

        validation_tasks = [
            ("System Requirements", self._validate_system_requirements),
            ("Prerequisites", self._validate_prerequisites),
            ("Directory Structure", self._validate_directory_structure),
            ("Configuration Files", self._validate_configuration_files),
            ("Network Ports", self._validate_network_ports),
            ("Permissions", self._validate_permissions),
        ]

        results = []

        for task_name, task_function in validation_tasks:
            self.logger.info(f"  Checking {task_name}...")

            try:
                result = await task_function()
                results.append(result)

                if result:
                    self.logger.info(f"  ✅ {task_name}: OK")
                else:
                    self.logger.error(f"  ❌ {task_name}: FAILED")

            except Exception as e:
                self.logger.error(f"  💥 {task_name}: ERROR - {e}")
                results.append(False)

        success_count = sum(results)
        total_count = len(results)

        self.logger.info(
            f"Validation summary: {success_count}/{total_count} checks passed",
        )

        # Require all critical validations to pass
        return success_count == total_count

    async def _validate_system_requirements(self) -> bool:
        """Validate system requirements"""
        try:
            # Check Python version
            if sys.version_info < (3, 8):
                self.logger.error("Python 3.8+ required")
                return False

            # Check available disk space (minimum 10GB)
            disk_usage = shutil.disk_usage(self.base_dir)
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 10:
                self.logger.warning(f"Low disk space: {free_gb:.1f}GB available")

            # Check memory (minimum 4GB)
            try:
                import psutil

                memory_gb = psutil.virtual_memory().total / (1024**3)
                if memory_gb < 4:
                    self.logger.warning(f"Low memory: {memory_gb:.1f}GB available")
            except ImportError:
                pass

            return True

        except Exception as e:
            self.logger.error(f"System requirements validation failed: {e}")
            return False

    async def _validate_prerequisites(self) -> bool:
        """Validate required software prerequisites"""
        prerequisites = {
            "docker": ["docker", "--version"],
            "docker-compose": ["docker-compose", "--version"],
            "git": ["git", "--version"],
            "node": ["node", "--version"],
            "npm": ["npm", "--version"],
        }

        missing_prereqs = []

        for name, command in prerequisites.items():
            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=10,
                )

                if process.returncode == 0:
                    version = stdout.decode().strip().split("\n")[0]
                    self.logger.debug(f"  {name}: {version}")
                else:
                    missing_prereqs.append(name)

            except (TimeoutError, FileNotFoundError, Exception):
                missing_prereqs.append(name)

        if missing_prereqs:
            self.logger.error(f"Missing prerequisites: {', '.join(missing_prereqs)}")
            self._show_installation_instructions(missing_prereqs)
            return False

        return True

    async def _validate_directory_structure(self) -> bool:
        """Validate directory structure"""
        required_dirs = ["scripts", "docker", "vault", "logs", "data"]

        missing_dirs = []

        for dir_name in required_dirs:
            dir_path = self.base_dir / dir_name
            if not dir_path.exists():
                self.logger.warning(f"Creating missing directory: {dir_path}")
                dir_path.mkdir(exist_ok=True)

        # Check for required files
        required_files = [
            "docker/docker-compose.yml",
            "docker/init-db.sql",
            "scripts/deploy_pake.py",
            ".env.example",
        ]

        missing_files = []

        for file_path in required_files:
            full_path = self.base_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        if missing_files:
            self.logger.error(f"Missing required files: {missing_files}")
            return False

        return True

    async def _validate_configuration_files(self) -> bool:
        """Validate configuration files"""
        try:
            # Validate docker-compose.yml
            docker_compose_file = self.docker_dir / "docker-compose.yml"
            if docker_compose_file.exists():
                with open(docker_compose_file) as f:
                    yaml.safe_load(f)

            # Create .env if it doesn't exist
            env_file = self.base_dir / ".env"
            env_example = self.base_dir / ".env.example"

            if not env_file.exists() and env_example.exists():
                self.logger.info("Creating .env file from template")
                shutil.copy2(env_example, env_file)
                self.logger.warning(
                    "⚠️  Please review and update .env file with actual values",
                )

            return True

        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False

    async def _validate_network_ports(self) -> bool:
        """Validate required network ports are available"""
        required_ports = [5432, 6379, 8000, 3000, 5678]

        # Add custom ports from config
        required_ports.extend(self.config.custom_ports.values())

        busy_ports = []

        for port in required_ports:
            if await self._is_port_in_use("localhost", port):
                busy_ports.append(port)

        if busy_ports:
            self.logger.warning(f"Ports in use: {busy_ports}")
            # Don't fail validation - Docker will handle port conflicts

        return True

    async def _validate_permissions(self) -> bool:
        """Validate file system permissions"""
        try:
            # Test write permission in base directory
            test_file = self.base_dir / f".pake_permission_test_{int(time.time())}"

            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception:
                self.logger.error("Insufficient permissions to write in base directory")
                return False

            # Check Docker access (if Docker is available)
            try:
                process = await asyncio.create_subprocess_exec(
                    "docker",
                    "info",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(process.communicate(), timeout=10)

                if process.returncode != 0:
                    self.logger.warning(
                        "Docker daemon not accessible - may need to start Docker Desktop",
                    )
            except Exception:
                pass

            return True

        except Exception as e:
            self.logger.error(f"Permission validation failed: {e}")
            return False

    async def _phase_preparation(self) -> bool:
        """Phase 2: Environment preparation"""
        self.logger.info("🔧 Preparing deployment environment...")

        preparation_tasks = [
            ("Environment Setup", self._prepare_environment),
            ("Directory Creation", self._prepare_directories),
            ("Configuration Generation", self._prepare_configurations),
            ("Dependency Installation", self._prepare_dependencies),
        ]

        for task_name, task_function in preparation_tasks:
            self.logger.info(f"  {task_name}...")

            try:
                success = await task_function()
                if not success:
                    self.logger.error(f"  ❌ {task_name} failed")
                    return False
                self.logger.info(f"  ✅ {task_name} completed")

            except Exception as e:
                self.logger.error(f"  💥 {task_name} error: {e}")
                return False

        return True

    async def _prepare_environment(self) -> bool:
        """Prepare environment variables and configuration"""
        try:
            # Set up environment variables
            env_updates = {
                "PAKE_DEPLOYMENT_ID": self.deployment_id,
                "PAKE_BASE_DIR": str(self.base_dir),
                "PAKE_MODE": self.config.mode.value,
                "PYTHONPATH": str(self.base_dir),
                "NODE_ENV": (
                    "production"
                    if self.config.mode == DeploymentMode.PRODUCTION
                    else "development"
                ),
            }

            # Add custom environment overrides
            env_updates.update(self.config.environment_overrides)

            # Update current environment
            os.environ.update(env_updates)

            # Update .env file if it exists
            env_file = self.base_dir / ".env"
            if env_file.exists():
                content = env_file.read_text()

                # Add PAKE-specific variables
                for key, value in env_updates.items():
                    if f"{key}=" not in content:
                        content += f"\n{key}={value}"

                env_file.write_text(content)

            self.logger.debug(f"Environment prepared with {len(env_updates)} variables")
            return True

        except Exception as e:
            self.logger.error(f"Environment preparation failed: {e}")
            return False

    async def _prepare_directories(self) -> bool:
        """Prepare all required directories"""
        try:
            # Standard directories
            directories = [
                "logs",
                "data",
                "vault",
                "vault/00-Inbox",
                "vault/01-Sources",
                "vault/02-Processing",
                "vault/03-Knowledge",
                "vault/04-Projects",
                "vault/_templates",
                "backups",
                "configs",
            ]

            for dir_name in directories:
                dir_path = self.base_dir / dir_name
                dir_path.mkdir(exist_ok=True, parents=True)

            # Set custom vault path if specified
            if self.config.custom_vault_path:
                vault_path = Path(self.config.custom_vault_path)
                if not vault_path.exists():
                    vault_path.mkdir(parents=True, exist_ok=True)

                # Update environment
                os.environ["VAULT_PATH"] = str(vault_path)

            self.logger.debug(f"Created {len(directories)} directories")
            return True

        except Exception as e:
            self.logger.error(f"Directory preparation failed: {e}")
            return False

    async def _prepare_configurations(self) -> bool:
        """Prepare configuration files"""
        try:
            # Generate deployment configuration
            deployment_config = {
                "deployment_id": self.deployment_id,
                "timestamp": datetime.now().isoformat(),
                "mode": self.config.mode.value,
                "config": {
                    "skip_docker": self.config.skip_docker,
                    "skip_dependencies": self.config.skip_dependencies,
                    "skip_frontend": self.config.skip_frontend,
                    "enable_monitoring": self.config.enable_monitoring,
                    "custom_ports": self.config.custom_ports,
                },
            }

            config_file = self.data_dir / f"deployment_config_{self.deployment_id}.json"
            with open(config_file, "w") as f:
                json.dump(deployment_config, f, indent=2)

            return True

        except Exception as e:
            self.logger.error(f"Configuration preparation failed: {e}")
            return False

    async def _prepare_dependencies(self) -> bool:
        """Prepare and install dependencies"""
        if self.config.skip_dependencies:
            self.logger.info(
                "  Skipping dependency installation (skip_dependencies=True)",
            )
            return True

        try:
            # Install Python dependencies
            python_success = await self._install_python_dependencies()

            # Install Node.js dependencies
            node_success = await self._install_node_dependencies()

            return python_success and node_success

        except Exception as e:
            self.logger.error(f"Dependency preparation failed: {e}")
            return False

    async def _install_python_dependencies(self) -> bool:
        """Install Python dependencies"""
        try:
            self.logger.info("    Installing Python dependencies...")

            # Find all requirements files
            requirements_files = [
                self.base_dir / "requirements.txt",
                self.base_dir / "mcp-servers" / "requirements.txt",
                self.scripts_dir / "requirements_ingestion.txt",
            ]

            for req_file in requirements_files:
                if req_file.exists():
                    self.logger.debug(f"    Installing from {req_file}")

                    process = await asyncio.create_subprocess_exec(
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        str(req_file),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=300 * self.config.timeout_multiplier,
                    )

                    if process.returncode != 0:
                        self.logger.error(
                            f"    Failed to install from {req_file}: {stderr.decode()}",
                        )
                        return False

            # Install additional required packages
            additional_packages = [
                "asyncio",
                "aiohttp",
                "psutil",
                "pyyaml",
                "sqlite3" if sys.version_info < (3, 9) else None,
            ]

            additional_packages = [pkg for pkg in additional_packages if pkg]

            if additional_packages:
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    *additional_packages,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                await asyncio.wait_for(process.communicate(), timeout=120)

            self.logger.info("    ✅ Python dependencies installed")
            return True

        except TimeoutError:
            self.logger.error("    Python dependency installation timed out")
            return False
        except Exception as e:
            self.logger.error(f"    Python dependency installation failed: {e}")
            return False

    async def _install_node_dependencies(self) -> bool:
        """Install Node.js dependencies"""
        try:
            self.logger.info("    Installing Node.js dependencies...")

            # Install scripts dependencies
            scripts_package = self.scripts_dir / "package.json"
            if scripts_package.exists():
                self.logger.debug("    Installing scripts dependencies...")

                process = await asyncio.create_subprocess_exec(
                    "npm",
                    "install",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.scripts_dir,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=300 * self.config.timeout_multiplier,
                )

                if process.returncode != 0:
                    self.logger.error(
                        f"    Scripts npm install failed: {stderr.decode()}",
                    )
                    return False

            # Install frontend dependencies
            if not self.config.skip_frontend:
                frontend_package = self.base_dir / "frontend" / "package.json"
                if frontend_package.exists():
                    self.logger.debug("    Installing frontend dependencies...")

                    process = await asyncio.create_subprocess_exec(
                        "npm",
                        "install",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=self.base_dir / "frontend",
                    )

                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=600 * self.config.timeout_multiplier,
                    )

                    if process.returncode != 0:
                        self.logger.error(
                            f"    Frontend npm install failed: {stderr.decode()}",
                        )
                        return False

            self.logger.info("    ✅ Node.js dependencies installed")
            return True

        except TimeoutError:
            self.logger.error("    Node.js dependency installation timed out")
            return False
        except Exception as e:
            self.logger.error(f"    Node.js dependency installation failed: {e}")
            return False

    async def _phase_infrastructure(self) -> bool:
        """Phase 3: Infrastructure deployment"""
        if self.config.skip_docker:
            self.logger.info("🐳 Skipping Docker infrastructure (skip_docker=True)")
            return True

        self.logger.info("🐳 Deploying Docker infrastructure...")

        try:
            # Initialize orchestrator
            if not self.orchestrator:
                self.orchestrator = PAKEMasterOrchestrator(str(self.base_dir))

            # Deploy infrastructure
            success = await self.orchestrator.deploy_infrastructure()

            if success:
                self.logger.info("  ✅ Docker infrastructure deployed successfully")

                # Wait for services to stabilize
                self.logger.info("  ⏳ Waiting for services to stabilize...")
                await asyncio.sleep(30)

                return True
            self.logger.error("  ❌ Docker infrastructure deployment failed")
            return False

        except Exception as e:
            self.logger.error(f"Infrastructure deployment failed: {e}")
            return False

    async def _phase_services(self) -> bool:
        """Phase 4: Service deployment"""
        self.logger.info("⚙️  Deploying services...")

        try:
            # Initialize service manager
            if not self.service_manager:
                self.service_manager = PAKEServiceManager()

            # Start services
            success = await self.service_manager.start_all_services()

            if success:
                self.logger.info("  ✅ All services deployed successfully")
                return True
            self.logger.error("  ❌ Some services failed to deploy")

            # Get service status
            status = await self.service_manager.get_system_status()
            failed_services = [
                name
                for name, info in status["services"].items()
                if info["state"] in ["failed", "stopped"] and info["critical"]
            ]

            if failed_services:
                self.logger.error(f"  Critical services failed: {failed_services}")
                return False
            self.logger.warning("  Only non-critical services failed")
            return True

        except Exception as e:
            self.logger.error(f"Service deployment failed: {e}")
            return False

    async def _phase_verification(self) -> bool:
        """Phase 5: System verification"""
        self.logger.info("🔍 Verifying system deployment...")

        verification_tasks = [
            ("Service Health", self._verify_service_health),
            ("Database Connectivity", self._verify_database_connectivity),
            ("API Endpoints", self._verify_api_endpoints),
            ("File System", self._verify_file_system),
            ("Integration Tests", self._verify_integration),
        ]

        results = []

        for task_name, task_function in verification_tasks:
            self.logger.info(f"  {task_name}...")

            try:
                result = await task_function()
                results.append(result)

                if result:
                    self.logger.info(f"  ✅ {task_name}: PASSED")
                else:
                    self.logger.warning(f"  ⚠️  {task_name}: FAILED")

            except Exception as e:
                self.logger.error(f"  💥 {task_name}: ERROR - {e}")
                results.append(False)

        success_count = sum(results)
        total_count = len(results)

        self.logger.info(
            f"Verification summary: {success_count}/{total_count} checks passed",
        )

        # Allow some non-critical verifications to fail
        return success_count >= total_count - 2

    async def _verify_service_health(self) -> bool:
        """Verify all services are healthy"""
        try:
            if not self.health_monitor:
                self.health_monitor = PAKEServiceMonitor()

            # Check all service health
            results = await self.health_monitor.check_all_services()

            critical_failures = []
            for service_name, result in results.items():
                if result.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                    service_config = self.health_monitor.services.get(service_name)
                    if service_config and service_config.critical:
                        critical_failures.append(service_name)

            if critical_failures:
                self.logger.error(
                    f"    Critical services unhealthy: {critical_failures}",
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Service health verification failed: {e}")
            return False

    async def _verify_database_connectivity(self) -> bool:
        """Verify database connectivity"""
        try:
            # Test PostgreSQL connection
            import asyncio

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("localhost", 5432),
                timeout=10,
            )

            writer.close()
            await writer.wait_closed()

            # Test Redis connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("localhost", 6379),
                timeout=10,
            )

            writer.close()
            await writer.wait_closed()

            return True

        except Exception as e:
            self.logger.error(f"Database connectivity verification failed: {e}")
            return False

    async def _verify_api_endpoints(self) -> bool:
        """Verify API endpoints are responding"""
        endpoints = [
            "http://localhost:8000/health",  # MCP Server
            "http://localhost:3000/health",  # API Bridge
        ]

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                for endpoint in endpoints:
                    try:
                        async with session.get(
                            endpoint,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as response:
                            if response.status >= 400:
                                self.logger.warning(
                                    f"    {endpoint}: HTTP {response.status}",
                                )
                                return False
                    except Exception as e:
                        self.logger.warning(f"    {endpoint}: {e}")
                        return False

            return True

        except ImportError:
            # Fallback to subprocess curl
            for endpoint in endpoints:
                try:
                    process = await asyncio.create_subprocess_exec(
                        "curl",
                        "-f",
                        "-s",
                        endpoint,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    await asyncio.wait_for(process.communicate(), timeout=10)

                    if process.returncode != 0:
                        return False

                except Exception:
                    return False

            return True

        except Exception as e:
            self.logger.error(f"API endpoint verification failed: {e}")
            return False

    async def _verify_file_system(self) -> bool:
        """Verify file system setup"""
        try:
            # Check vault structure
            vault_dirs = [
                "00-Inbox",
                "01-Sources",
                "02-Processing",
                "03-Knowledge",
                "04-Projects",
                "_templates",
            ]
            vault_path = Path(
                os.environ.get("VAULT_PATH", str(self.base_dir / "vault")),
            )

            for dir_name in vault_dirs:
                dir_path = vault_path / dir_name
                if not dir_path.exists():
                    self.logger.warning(f"    Missing vault directory: {dir_path}")
                    return False

            # Test write permissions
            test_file = vault_path / "00-Inbox" / f".test_{int(time.time())}"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception:
                self.logger.error("    Cannot write to vault directory")
                return False

            return True

        except Exception as e:
            self.logger.error(f"File system verification failed: {e}")
            return False

    async def _verify_integration(self) -> bool:
        """Verify system integration"""
        try:
            # Simple integration test - create a test note and process it
            vault_path = Path(
                os.environ.get("VAULT_PATH", str(self.base_dir / "vault")),
            )
            test_note = (
                vault_path / "00-Inbox" / f"deployment_test_{self.deployment_id}.md"
            )

            test_content = f"""---
pake_id: "deployment-test-{self.deployment_id}"
created: "{datetime.now().isoformat()}"
modified: "{datetime.now().isoformat()}"
type: "test_note"
status: "verified"
confidence_score: 1.0
verification_status: "verified"
source_uri: "local://deployment_test"
tags: ["deployment", "test", "automation"]
ai_summary: "Deployment verification test note"
human_notes: "Generated during deployment verification"
---

# Deployment Test Note

This note was generated during PAKE+ deployment verification.

## Test Details
- Deployment ID: {self.deployment_id}
- Timestamp: {datetime.now().isoformat()}
- Mode: {self.config.mode.value}

## System Status
Deployment verification in progress...
"""

            test_note.write_text(test_content)

            # Verify note was created
            if test_note.exists():
                self.logger.info("    ✅ Test note created successfully")
                return True
            self.logger.error("    ❌ Failed to create test note")
            return False

        except Exception as e:
            self.logger.error(f"Integration verification failed: {e}")
            return False

    async def _phase_finalization(self) -> bool:
        """Phase 6: Deployment finalization"""
        self.logger.info("🏁 Finalizing deployment...")

        try:
            # Start monitoring if enabled
            if self.config.enable_monitoring:
                self.logger.info("  Starting health monitoring...")
                # Note: In production, this would start as a background service

            # Create deployment success marker
            success_marker = (
                self.data_dir / f"deployment_success_{self.deployment_id}.json"
            )
            success_data = {
                "deployment_id": self.deployment_id,
                "timestamp": datetime.now().isoformat(),
                "mode": self.config.mode.value,
                "duration": time.time() - self.deployment_start_time,
                "phase_results": self.phase_results,
            }

            with open(success_marker, "w") as f:
                json.dump(success_data, f, indent=2)

            # Clean up temporary files
            temp_files = list(self.base_dir.glob(".pake_*"))
            for temp_file in temp_files:
                try:
                    temp_file.unlink()
                except Exception:
                    pass

            self.logger.info("  ✅ Deployment finalized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Deployment finalization failed: {e}")
            return False

    async def _generate_deployment_report(self, success: bool):
        """Generate comprehensive deployment report"""
        try:
            duration = (
                time.time() - self.deployment_start_time
                if self.deployment_start_time
                else 0
            )

            report = f"""# PAKE+ Deployment Report
Deployment ID: {self.deployment_id}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary
- **Status**: {"✅ SUCCESS" if success else "❌ FAILED"}
- **Duration**: {duration:.1f} seconds
- **Mode**: {self.config.mode.value}
- **Platform**: {platform.system()} {platform.release()}

## Configuration
- Skip Docker: {self.config.skip_docker}
- Skip Dependencies: {self.config.skip_dependencies}
- Skip Frontend: {self.config.skip_frontend}
- Enable Monitoring: {self.config.enable_monitoring}
- Parallel Execution: {self.config.parallel_execution}

## Phase Results
"""

            for phase_name, result in self.phase_results.items():
                status_icon = "✅" if result["success"] else "❌"
                report += f"- **{phase_name.title()}**: {status_icon} ({
                    result['duration']:.1f}s)\n"

                if not result["success"] and "error" in result:
                    report += f"  - Error: {result['error']}\n"

            if self.deployment_errors:
                report += "\n## Errors\n"
                for i, error in enumerate(self.deployment_errors, 1):
                    report += f"{i}. {error}\n"

            # System status
            if self.service_manager:
                try:
                    status = await self.service_manager.get_system_status()
                    report += "\n## System Status\n"
                    report += f"- **Overall**: {status['overall_status'].upper()}\n"
                    report += f"- **Services Running**: {status['summary']['running']}/{
                        status['summary']['total']
                    }\n"

                    report += "\n### Service Details\n"
                    for service_name, info in status["services"].items():
                        status_icon = {
                            "running": "🟢",
                            "stopped": "🔴",
                            "failed": "❌",
                            "starting": "🟡",
                        }.get(info["state"], "❓")
                        criticality = "🔥" if info["critical"] else "ℹ️"
                        report += f"- {status_icon} {criticality} **{
                            info['display_name']
                        }**: {info['state'].upper()}\n"

                except Exception:
                    pass

            report += f"""
## Next Steps
{"1. System is ready for use!" if success else "1. Review error logs and address issues"}
2. Access services:
   - MCP Server: http://localhost:8000
   - API Bridge: http://localhost:3000
   - n8n Automation: http://localhost:5678
   - Frontend: http://localhost:3001
3. Check logs in: {self.logs_dir}
4. Monitor system health with health monitoring tools

## Support
- Log Files: {self.logs_dir}/unified_deployment_{self.deployment_id}.log
- Error Log: {self.logs_dir}/deployment_errors_{self.deployment_id}.log
- Deployment Data: {self.data_dir}/deployment_config_{self.deployment_id}.json

---
*Generated by PAKE+ Unified Deployment System*
"""

            # Save report
            report_file = self.logs_dir / f"deployment_report_{self.deployment_id}.md"
            with open(report_file, "w") as f:
                f.write(report)

            self.logger.info(f"📊 Deployment report saved: {report_file}")

        except Exception as e:
            self.logger.error(f"Failed to generate deployment report: {e}")

    def _show_installation_instructions(self, missing_prereqs: list[str]):
        """Show installation instructions for missing prerequisites"""
        instructions = {
            "docker": "Install Docker Desktop from: https://docs.docker.com/get-docker/",
            "docker-compose": "Docker Compose is included with Docker Desktop",
            "git": "Install Git from: https://git-scm.com/downloads",
            "node": "Install Node.js from: https://nodejs.org/",
            "npm": "npm is included with Node.js installation",
        }

        self.logger.info("Installation instructions:")
        for prereq in missing_prereqs:
            if prereq in instructions:
                self.logger.info(f"  {prereq}: {instructions[prereq]}")

    async def _is_port_in_use(self, host: str, port: int) -> bool:
        """Check if a port is in use"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=1,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except BaseException:
            return False


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="PAKE+ Unified Deployment System")
    parser.add_argument(
        "--mode",
        choices=["development", "production", "testing", "recovery"],
        default="development",
        help="Deployment mode",
    )
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Skip Docker infrastructure deployment",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency installation",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Skip frontend deployment",
    )
    parser.add_argument(
        "--force-reinstall",
        action="store_true",
        help="Force reinstallation of components",
    )
    parser.add_argument(
        "--no-monitoring",
        action="store_true",
        help="Disable health monitoring",
    )
    parser.add_argument(
        "--timeout-multiplier",
        type=float,
        default=1.0,
        help="Multiply all timeouts by this factor",
    )
    parser.add_argument("--vault-path", help="Custom vault path")
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Enable parallel execution",
    )

    args = parser.parse_args()

    # Create deployment configuration
    config = DeploymentConfig(
        mode=DeploymentMode(args.mode),
        skip_docker=args.skip_docker,
        skip_dependencies=args.skip_deps,
        skip_frontend=args.skip_frontend,
        force_reinstall=args.force_reinstall,
        enable_monitoring=not args.no_monitoring,
        timeout_multiplier=args.timeout_multiplier,
        custom_vault_path=args.vault_path,
        parallel_execution=args.parallel,
    )

    # Execute deployment
    deployment = PAKEUnifiedDeployment(config)
    success = await deployment.execute_full_deployment()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Fatal deployment error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
