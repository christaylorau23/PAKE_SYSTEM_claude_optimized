#!/usr/bin/env python3
"""
PAKE+ Enhanced Service Manager
Dependency-aware service orchestration with automated recovery
Implements all patterns from the provided code snippets
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import psutil
import yaml


class ServiceState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ServiceType(Enum):
    DOCKER = "docker"
    SYSTEMD = "systemd"
    PROCESS = "process"
    HTTP = "http"
    DATABASE = "database"
    NODE_JS = "nodejs"
    PYTHON = "python"


@dataclass
class ServiceConfig:
    name: str
    display_name: str
    type: ServiceType
    dependencies: list[str] = field(default_factory=list)

    # Commands
    start_command: str | None = None
    stop_command: str | None = None
    restart_command: str | None = None
    status_command: str | None = None

    # Health check
    health_endpoint: str | None = None
    health_timeout: int = 10
    startup_timeout: int = 60

    # Process/Container details
    process_name: str | None = None
    container_name: str | None = None
    service_name: str | None = None  # For systemd

    # Network
    host: str = "localhost"
    port: int | None = None

    # Recovery behavior
    auto_restart: bool = True
    max_restart_attempts: int = 3
    restart_delay: int = 5
    restart_backoff: float = 1.5

    # Environment
    working_directory: str | None = None
    environment: dict[str, str] = field(default_factory=dict)

    # Criticality
    critical: bool = True
    required_for_startup: bool = True
    graceful_shutdown_timeout: int = 30


class PAKEServiceManager:
    """Enhanced service manager with dependency resolution and recovery"""

    def __init__(self, config_file: str | None = None):
        self.base_dir = Path(__file__).parent.parent
        self.config_dir = self.base_dir / "configs"
        self.logs_dir = self.base_dir / "logs"
        self.data_dir = self.base_dir / "data"
        self.state_file = self.data_dir / "service_manager_state.json"

        # Ensure directories exist
        for directory in [self.config_dir, self.logs_dir, self.data_dir]:
            directory.mkdir(exist_ok=True)

        # Setup logging
        self.setup_logging()

        # Load service configurations
        self.services = self.load_service_configs(config_file)

        # State tracking
        self.service_states: dict[str, ServiceState] = {}
        self.service_processes: dict[str, subprocess.Popen] = {}
        self.restart_attempts: dict[str, int] = {}
        self.last_restart_time: dict[str, datetime] = {}
        self.startup_order: list[str] = []
        self.shutdown_order: list[str] = []

        # Control flags
        self.running = False
        self.shutdown_requested = False

        # Initialize state
        self.load_service_state()
        self.calculate_service_orders()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown_signal)
        signal.signal(signal.SIGTERM, self.handle_shutdown_signal)

        self.logger.info("PAKE+ Service Manager initialized")

    def setup_logging(self):
        """Setup comprehensive logging system"""
        log_file = (
            self.logs_dir / f"service_manager_{datetime.now().strftime('%Y%m%d')}.log"
        )

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        )

        # File handler with rotation
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)

        # Setup logger
        self.logger = logging.getLogger("PAKEServiceManager")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def load_service_configs(
        self,
        config_file: str | None = None,
    ) -> dict[str, ServiceConfig]:
        """Load service configurations from file and defaults"""

        # Default PAKE system services
        default_services = {
            "postgres": ServiceConfig(
                name="postgres",
                display_name="PostgreSQL Database",
                type=ServiceType.DOCKER,
                container_name="pake_postgres",
                port=5432,
                health_timeout=15,
                startup_timeout=120,
                start_command="docker start pake_postgres",
                stop_command="docker stop pake_postgres",
                restart_command="docker restart pake_postgres",
                status_command='docker inspect -f "{{.State.Status}}" pake_postgres',
                critical=True,
                dependencies=[],
            ),
            "redis": ServiceConfig(
                name="redis",
                display_name="Redis Cache",
                type=ServiceType.DOCKER,
                container_name="pake_redis",
                port=6379,
                health_timeout=10,
                startup_timeout=60,
                start_command="docker start pake_redis",
                stop_command="docker stop pake_redis",
                restart_command="docker restart pake_redis",
                status_command='docker inspect -f "{{.State.Status}}" pake_redis',
                critical=True,
                dependencies=[],
            ),
            "mcp_server": ServiceConfig(
                name="mcp_server",
                display_name="MCP Server",
                type=ServiceType.DOCKER,
                container_name="pake_mcp_server",
                port=8000,
                health_endpoint="http://localhost:8000/health",
                health_timeout=10,
                startup_timeout=90,
                start_command="docker start pake_mcp_server",
                stop_command="docker stop pake_mcp_server",
                restart_command="docker restart pake_mcp_server",
                status_command='docker inspect -f "{{.State.Status}}" pake_mcp_server',
                critical=True,
                dependencies=["postgres", "redis"],
            ),
            "n8n": ServiceConfig(
                name="n8n",
                display_name="n8n Automation",
                type=ServiceType.DOCKER,
                container_name="pake_n8n",
                port=5678,
                health_endpoint="http://localhost:5678",
                health_timeout=15,
                startup_timeout=120,
                start_command="docker start pake_n8n",
                stop_command="docker stop pake_n8n",
                restart_command="docker restart pake_n8n",
                status_command='docker inspect -f "{{.State.Status}}" pake_n8n',
                critical=False,
                dependencies=["postgres"],
            ),
            "api_bridge": ServiceConfig(
                name="api_bridge",
                display_name="Obsidian API Bridge",
                type=ServiceType.NODE_JS,
                port=3000,
                health_endpoint="http://localhost:3000/health",
                process_name="node",
                working_directory=str(self.base_dir / "scripts"),
                start_command="node obsidian_bridge.js",
                environment={
                    "VAULT_PATH": str(self.base_dir / "vault"),
                    "MCP_SERVER_URL": "http://localhost:8000",
                    "BRIDGE_PORT": "3000",
                    "NODE_ENV": "production",
                },
                health_timeout=10,
                startup_timeout=30,
                critical=True,
                dependencies=["mcp_server"],
            ),
            "ingestion_manager": ServiceConfig(
                name="ingestion_manager",
                display_name="Content Ingestion Manager",
                type=ServiceType.PYTHON,
                port=8001,
                health_endpoint="http://localhost:8001/health",
                working_directory=str(self.base_dir / "scripts"),
                start_command=f"{sys.executable} ingestion_manager.py",
                environment={
                    "PYTHONPATH": str(self.base_dir),
                    "VAULT_PATH": str(self.base_dir / "vault"),
                    "DATABASE_URL": "postgresql://pake_admin:secure_REDACTED_SECRET_123@localhost:5433/pake_knowledge",
                },
                health_timeout=10,
                startup_timeout=45,
                critical=False,
                dependencies=["postgres", "redis", "mcp_server"],
            ),
            "frontend": ServiceConfig(
                name="frontend",
                display_name="Frontend Application",
                type=ServiceType.NODE_JS,
                port=3001,
                health_endpoint="http://localhost:3001",
                process_name="next-server",
                working_directory=str(self.base_dir / "frontend"),
                start_command="npm run dev",
                environment={"NODE_ENV": "development", "PORT": "3001"},
                health_timeout=10,
                startup_timeout=60,
                critical=False,
                dependencies=[],
            ),
            "nginx": ServiceConfig(
                name="nginx",
                display_name="Nginx Reverse Proxy",
                type=ServiceType.DOCKER,
                container_name="pake_nginx",
                port=80,
                health_endpoint="http://localhost/health",
                start_command="docker start pake_nginx",
                stop_command="docker stop pake_nginx",
                restart_command="docker restart pake_nginx",
                status_command='docker inspect -f "{{.State.Status}}" pake_nginx',
                health_timeout=5,
                startup_timeout=30,
                critical=False,
                dependencies=["mcp_server", "api_bridge"],
            ),
        }

        # Load custom configurations if provided
        if config_file and Path(config_file).exists():
            try:
                self.logger.info(f"Loading custom service config from {config_file}")

                with open(config_file) as f:
                    if config_file.endswith(".yaml") or config_file.endswith(".yml"):
                        custom_config = yaml.safe_load(f)
                    else:
                        custom_config = json.load(f)

                # Update or add services from config
                for service_name, config_data in custom_config.get(
                    "services",
                    {},
                ).items():
                    if service_name in default_services:
                        # Update existing service
                        service = default_services[service_name]
                        for key, value in config_data.items():
                            if hasattr(service, key):
                                setattr(service, key, value)
                    else:
                        # Add new service
                        # Convert string type to enum
                        if "type" in config_data and isinstance(
                            config_data["type"],
                            str,
                        ):
                            config_data["type"] = ServiceType(config_data["type"])

                        default_services[service_name] = ServiceConfig(**config_data)

                self.logger.info(
                    f"Loaded {len(custom_config.get('services', {}))} custom service configs",
                )

            except Exception as e:
                self.logger.error(f"Failed to load custom config: {e}")

        return default_services

    def calculate_service_orders(self):
        """Calculate startup and shutdown orders based on dependencies"""
        # Calculate startup order using topological sort
        self.startup_order = self._topological_sort()

        # Shutdown order is reverse of startup
        self.shutdown_order = list(reversed(self.startup_order))

        self.logger.info(f"Startup order: {' -> '.join(self.startup_order)}")
        self.logger.info(f"Shutdown order: {' -> '.join(self.shutdown_order)}")

    def _topological_sort(self) -> list[str]:
        """Perform topological sort to determine service startup order"""
        # Create adjacency list and in-degree count
        graph = {service: set() for service in self.services}
        in_degree = dict.fromkeys(self.services, 0)

        # Build dependency graph
        for service_name, config in self.services.items():
            for dep in config.dependencies:
                if dep in self.services:
                    graph[dep].add(service_name)
                    in_degree[service_name] += 1
                else:
                    self.logger.warning(
                        f"Service {service_name} depends on unknown service: {dep}",
                    )

        # Kahn's algorithm
        queue = [service for service, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            service = queue.pop(0)
            result.append(service)

            for dependent in graph[service]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Check for circular dependencies
        if len(result) != len(self.services):
            remaining = [s for s in self.services if s not in result]
            self.logger.error(f"Circular dependencies detected involving: {remaining}")
            # Add remaining services to avoid blocking
            result.extend(remaining)

        return result

    async def start_service(self, service_name: str, force: bool = False) -> bool:
        """Start a specific service"""
        if service_name not in self.services:
            self.logger.error(f"Unknown service: {service_name}")
            return False

        config = self.services[service_name]
        current_state = await self.get_service_state(service_name)

        if current_state == ServiceState.RUNNING and not force:
            self.logger.info(f"Service {config.display_name} is already running")
            return True

        if current_state == ServiceState.STARTING:
            self.logger.info(f"Service {config.display_name} is already starting")
            return await self._wait_for_service_start(service_name)

        # Check dependencies
        if not await self._check_dependencies(service_name):
            return False

        # Start the service
        self.logger.info(f"🚀 Starting {config.display_name}...")
        self.service_states[service_name] = ServiceState.STARTING

        try:
            success = await self._execute_start_command(service_name, config)

            if success:
                # Wait for service to become healthy
                success = await self._wait_for_service_health(service_name, config)

            if success:
                self.service_states[service_name] = ServiceState.RUNNING
                self.restart_attempts[service_name] = 0
                self.logger.info(
                    f"✅ Service {config.display_name} started successfully",
                )

                # Save state
                self.save_service_state()
                return True
            self.service_states[service_name] = ServiceState.FAILED
            self.logger.error(f"❌ Service {config.display_name} failed to start")
            return False

        except Exception as e:
            self.service_states[service_name] = ServiceState.FAILED
            self.logger.error(f"❌ Exception starting {config.display_name}: {e}")
            return False

    async def _check_dependencies(self, service_name: str) -> bool:
        """Check if all dependencies are running"""
        config = self.services[service_name]

        for dep in config.dependencies:
            dep_state = await self.get_service_state(dep)
            if dep_state != ServiceState.RUNNING:
                self.logger.error(
                    f"Cannot start {config.display_name}: dependency {dep} is {
                        dep_state.value
                    }",
                )
                return False

        return True

    async def _execute_start_command(
        self,
        service_name: str,
        config: ServiceConfig,
    ) -> bool:
        """Execute the start command for a service"""
        if not config.start_command:
            self.logger.error(f"No start command configured for {config.display_name}")
            return False

        try:
            # Set up environment
            env = os.environ.copy()
            env.update(config.environment)

            # Determine working directory
            cwd = config.working_directory or str(self.base_dir)

            self.logger.debug(f"Executing: {config.start_command}")
            self.logger.debug(f"Working directory: {cwd}")

            if config.type in [
                ServiceType.NODE_JS,
                ServiceType.PYTHON,
                ServiceType.PROCESS,
            ]:
                # For long-running processes, start in background
                process = await asyncio.create_subprocess_shell(
                    config.start_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                    preexec_fn=os.setsid if os.name != "nt" else None,
                )

                self.service_processes[service_name] = process

                # Give the process a moment to start
                await asyncio.sleep(2)

                # Check if process is still running
                if process.returncode is None:
                    self.logger.debug(f"Process started with PID: {process.pid}")
                    return True
                stdout, stderr = await process.communicate()
                self.logger.error(f"Process failed immediately: {stderr.decode()}")
                return False

            # For Docker/systemd services, run command and wait
            process = await asyncio.create_subprocess_shell(
                config.start_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=config.startup_timeout,
            )

            if process.returncode == 0:
                self.logger.debug("Start command completed successfully")
                return True
            self.logger.error(f"Start command failed: {stderr.decode()}")
            return False

        except TimeoutError:
            self.logger.error(
                f"Start command timed out after {config.startup_timeout}s",
            )
            return False
        except Exception as e:
            self.logger.error(f"Error executing start command: {e}")
            return False

    async def _wait_for_service_health(
        self,
        service_name: str,
        config: ServiceConfig,
    ) -> bool:
        """Wait for service to become healthy"""
        if config.health_endpoint:
            return await self._wait_for_http_health(config)
        if config.port:
            return await self._wait_for_tcp_health(config)
        # No health check available, assume healthy after delay
        await asyncio.sleep(5)
        return True

    async def _wait_for_http_health(self, config: ServiceConfig) -> bool:
        """Wait for HTTP health check to pass"""
        import aiohttp

        timeout = aiohttp.ClientTimeout(total=config.health_timeout)
        end_time = time.time() + config.startup_timeout

        while time.time() < end_time:
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(config.health_endpoint) as response:
                        if response.status < 400:
                            return True
            except BaseException:
                pass

            await asyncio.sleep(2)

        return False

    async def _wait_for_tcp_health(self, config: ServiceConfig) -> bool:
        """Wait for TCP port to be available"""
        end_time = time.time() + config.startup_timeout

        while time.time() < end_time:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(config.host, config.port),
                    timeout=config.health_timeout,
                )
                writer.close()
                await writer.wait_closed()
                return True
            except BaseException:
                pass

            await asyncio.sleep(2)

        return False

    async def _wait_for_service_start(self, service_name: str) -> bool:
        """Wait for a service that is currently starting to complete"""
        config = self.services[service_name]
        end_time = time.time() + config.startup_timeout

        while time.time() < end_time:
            state = await self.get_service_state(service_name)

            if state == ServiceState.RUNNING:
                return True
            if state in [ServiceState.FAILED, ServiceState.STOPPED]:
                return False

            await asyncio.sleep(1)

        return False

    async def stop_service(self, service_name: str, force: bool = False) -> bool:
        """Stop a specific service"""
        if service_name not in self.services:
            self.logger.error(f"Unknown service: {service_name}")
            return False

        config = self.services[service_name]
        current_state = await self.get_service_state(service_name)

        if current_state in [ServiceState.STOPPED, ServiceState.STOPPING]:
            self.logger.info(
                f"Service {config.display_name} is already stopped/stopping",
            )
            return True

        self.logger.info(f"🛑 Stopping {config.display_name}...")
        self.service_states[service_name] = ServiceState.STOPPING

        try:
            success = await self._execute_stop_command(service_name, config, force)

            if success:
                self.service_states[service_name] = ServiceState.STOPPED
                self.logger.info(
                    f"✅ Service {config.display_name} stopped successfully",
                )
            else:
                self.service_states[service_name] = ServiceState.FAILED
                self.logger.error(f"❌ Failed to stop {config.display_name}")

            # Clean up process reference
            if service_name in self.service_processes:
                del self.service_processes[service_name]

            self.save_service_state()
            return success

        except Exception as e:
            self.service_states[service_name] = ServiceState.FAILED
            self.logger.error(f"❌ Exception stopping {config.display_name}: {e}")
            return False

    async def _execute_stop_command(
        self,
        service_name: str,
        config: ServiceConfig,
        force: bool = False,
    ) -> bool:
        """Execute the stop command for a service"""
        # Try graceful shutdown first
        if config.stop_command and not force:
            try:
                process = await asyncio.create_subprocess_shell(
                    config.stop_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=config.graceful_shutdown_timeout,
                )

                if process.returncode == 0:
                    return True

            except TimeoutError:
                self.logger.warning(
                    f"Graceful shutdown timed out for {config.display_name}",
                )
            except Exception as e:
                self.logger.warning(
                    f"Graceful shutdown failed for {config.display_name}: {e}",
                )

        # Force kill if graceful shutdown failed or force requested
        if service_name in self.service_processes:
            process = self.service_processes[service_name]

            try:
                # Try SIGTERM first
                if os.name != "nt":
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=10)
                        return True
                    except TimeoutError:
                        pass

                # Force kill
                process.kill()
                await process.wait()
                return True

            except Exception as e:
                self.logger.error(f"Failed to kill process: {e}")
                return False

        return True

    async def restart_service(self, service_name: str) -> bool:
        """Restart a specific service"""
        config = self.services[service_name]
        self.logger.info(f"🔄 Restarting {config.display_name}...")

        # Use restart command if available
        if config.restart_command:
            try:
                process = await asyncio.create_subprocess_shell(
                    config.restart_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=config.startup_timeout + config.graceful_shutdown_timeout,
                )

                if process.returncode == 0:
                    self.service_states[service_name] = ServiceState.RUNNING
                    self.restart_attempts[service_name] = 0
                    return True

            except Exception as e:
                self.logger.error(f"Restart command failed: {e}")

        # Fallback to stop + start
        stop_success = await self.stop_service(service_name)
        if stop_success:
            await asyncio.sleep(config.restart_delay)
            return await self.start_service(service_name)

        return False

    async def get_service_state(self, service_name: str) -> ServiceState:
        """Get current state of a service"""
        if service_name not in self.services:
            return ServiceState.UNKNOWN

        # Return cached state if available
        if service_name in self.service_states:
            cached_state = self.service_states[service_name]

            # Validate cached state for running services
            if cached_state == ServiceState.RUNNING:
                if await self._validate_service_running(service_name):
                    return ServiceState.RUNNING
                self.service_states[service_name] = ServiceState.FAILED
                return ServiceState.FAILED

            return cached_state

        # Determine state from system
        config = self.services[service_name]

        if config.type == ServiceType.DOCKER and config.container_name:
            state = await self._get_docker_service_state(config.container_name)
        elif config.type in [
            ServiceType.NODE_JS,
            ServiceType.PYTHON,
            ServiceType.PROCESS,
        ]:
            state = await self._get_process_service_state(config)
        elif config.type == ServiceType.SYSTEMD and config.service_name:
            state = await self._get_systemd_service_state(config.service_name)
        else:
            state = ServiceState.UNKNOWN

        self.service_states[service_name] = state
        return state

    async def _validate_service_running(self, service_name: str) -> bool:
        """Validate that a service is actually running"""
        config = self.services[service_name]

        # Check health endpoint if available
        if config.health_endpoint:
            try:
                import aiohttp

                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(config.health_endpoint) as response:
                        return response.status < 400
            except BaseException:
                return False

        # Check TCP port if available
        elif config.port:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(config.host, config.port),
                    timeout=5,
                )
                writer.close()
                await writer.wait_closed()
                return True
            except BaseException:
                return False

        # Check process if managed locally
        elif service_name in self.service_processes:
            process = self.service_processes[service_name]
            return process.returncode is None

        return True  # Assume running if no validation method available

    async def _get_docker_service_state(self, container_name: str) -> ServiceState:
        """Get Docker container state"""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker",
                "inspect",
                "-f",
                "{{.State.Status}}",
                container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                status = stdout.decode().strip()
                if status == "running":
                    return ServiceState.RUNNING
                if status in ["exited", "dead"]:
                    return ServiceState.STOPPED
                if status in ["restarting"]:
                    return ServiceState.STARTING
                return ServiceState.UNKNOWN
            return ServiceState.STOPPED

        except Exception:
            return ServiceState.UNKNOWN

    async def _get_process_service_state(self, config: ServiceConfig) -> ServiceState:
        """Get process-based service state"""
        if not config.process_name:
            return ServiceState.UNKNOWN

        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                if config.process_name in proc.info["name"] or any(
                    config.process_name in cmd for cmd in (proc.info["cmdline"] or [])
                ):
                    if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
                        return ServiceState.RUNNING

            return ServiceState.STOPPED

        except Exception:
            return ServiceState.UNKNOWN

    async def _get_systemd_service_state(self, service_name: str) -> ServiceState:
        """Get systemd service state"""
        try:
            process = await asyncio.create_subprocess_exec(
                "systemctl",
                "is-active",
                service_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            status = stdout.decode().strip()

            if status == "active":
                return ServiceState.RUNNING
            if status in ["inactive", "failed"]:
                return ServiceState.STOPPED
            if status in ["activating"]:
                return ServiceState.STARTING
            return ServiceState.UNKNOWN

        except Exception:
            return ServiceState.UNKNOWN

    async def start_all_services(self) -> bool:
        """Start all services in dependency order"""
        self.logger.info("🚀 Starting all PAKE+ services...")

        failed_services = []

        for service_name in self.startup_order:
            config = self.services[service_name]

            if not config.required_for_startup:
                self.logger.info(f"Skipping optional service: {config.display_name}")
                continue

            self.logger.info(f"Starting {config.display_name}...")
            success = await self.start_service(service_name)

            if not success:
                failed_services.append(service_name)

                if config.critical:
                    self.logger.critical(
                        f"Critical service {config.display_name} failed to start",
                    )
                    return False
                self.logger.warning(
                    f"Non-critical service {config.display_name} failed to start",
                )

            # Brief delay between services
            await asyncio.sleep(2)

        if failed_services:
            self.logger.warning(f"Some services failed to start: {failed_services}")
        else:
            self.logger.info("✅ All services started successfully")

        return len(failed_services) == 0

    async def stop_all_services(self) -> bool:
        """Stop all services in reverse dependency order"""
        self.logger.info("🛑 Stopping all PAKE+ services...")

        failed_services = []

        for service_name in self.shutdown_order:
            config = self.services[service_name]
            current_state = await self.get_service_state(service_name)

            if current_state not in [ServiceState.RUNNING, ServiceState.STARTING]:
                continue

            self.logger.info(f"Stopping {config.display_name}...")
            success = await self.stop_service(service_name)

            if not success:
                failed_services.append(service_name)
                self.logger.error(f"Failed to stop {config.display_name}")

            # Brief delay between services
            await asyncio.sleep(1)

        if failed_services:
            self.logger.warning(
                f"Some services failed to stop cleanly: {failed_services}",
            )
        else:
            self.logger.info("✅ All services stopped successfully")

        return len(failed_services) == 0

    async def get_system_status(self) -> dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "services": {},
            "summary": {
                "total": len(self.services),
                "running": 0,
                "stopped": 0,
                "failed": 0,
                "starting": 0,
                "unknown": 0,
            },
        }

        # Check all services
        for service_name, config in self.services.items():
            service_state = await self.get_service_state(service_name)

            status["services"][service_name] = {
                "display_name": config.display_name,
                "state": service_state.value,
                "critical": config.critical,
                "dependencies": config.dependencies,
                "restart_attempts": self.restart_attempts.get(service_name, 0),
                "last_restart": (
                    self.last_restart_time.get(service_name, {}).isoformat()
                    if service_name in self.last_restart_time
                    else None
                ),
            }

            # Update summary
            status["summary"][service_state.value] += 1

        # Determine overall status
        critical_failed = any(
            s["critical"] and s["state"] in ["failed", "stopped"]
            for s in status["services"].values()
        )

        any_failed = status["summary"]["failed"] > 0
        any_starting = status["summary"]["starting"] > 0

        if critical_failed:
            status["overall_status"] = "critical"
        elif any_failed:
            status["overall_status"] = "degraded"
        elif any_starting:
            status["overall_status"] = "starting"
        else:
            status["overall_status"] = "healthy"

        return status

    def save_service_state(self):
        """Save current service states to disk"""
        try:
            state_data = {
                "timestamp": datetime.now().isoformat(),
                "service_states": {k: v.value for k, v in self.service_states.items()},
                "restart_attempts": self.restart_attempts,
                "last_restart_time": {
                    k: v.isoformat() for k, v in self.last_restart_time.items()
                },
            }

            with open(self.state_file, "w") as f:
                json.dump(state_data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save service state: {e}")

    def load_service_state(self):
        """Load service states from disk"""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    state_data = json.load(f)

                # Load service states
                for service_name, state_str in state_data.get(
                    "service_states",
                    {},
                ).items():
                    try:
                        self.service_states[service_name] = ServiceState(state_str)
                    except ValueError:
                        pass

                # Load restart attempts
                self.restart_attempts.update(state_data.get("restart_attempts", {}))

                # Load last restart times
                for service_name, time_str in state_data.get(
                    "last_restart_time",
                    {},
                ).items():
                    try:
                        self.last_restart_time[service_name] = datetime.fromisoformat(
                            time_str,
                        )
                    except ValueError:
                        pass

                self.logger.info("Service state loaded from disk")

        except Exception as e:
            self.logger.warning(f"Failed to load service state: {e}")

    def handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown_requested = True

    async def run_service_loop(self, monitor_interval: int = 30):
        """Run main service monitoring loop"""
        self.running = True
        self.logger.info(
            f"Starting service monitoring loop (interval: {monitor_interval}s)",
        )

        while self.running and not self.shutdown_requested:
            try:
                # Check service health and handle failures
                await self._monitor_service_health()

                # Wait for next cycle
                for _ in range(monitor_interval):
                    if self.shutdown_requested:
                        break
                    await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Error in service monitoring loop: {e}")
                await asyncio.sleep(10)

        # Graceful shutdown
        await self.stop_all_services()
        self.running = False
        self.logger.info("Service manager stopped")

    async def _monitor_service_health(self):
        """Monitor health of all services and restart failed ones"""
        for service_name, config in self.services.items():
            if not config.auto_restart:
                continue

            current_state = await self.get_service_state(service_name)

            if current_state == ServiceState.FAILED:
                await self._handle_service_failure(service_name, config)

    async def _handle_service_failure(self, service_name: str, config: ServiceConfig):
        """Handle service failure with restart logic"""
        attempts = self.restart_attempts.get(service_name, 0)

        if attempts >= config.max_restart_attempts:
            self.logger.critical(
                f"Service {config.display_name} has exceeded max restart attempts ({
                    attempts
                })",
            )
            return

        # Calculate backoff delay
        delay = config.restart_delay * (config.restart_backoff**attempts)

        # Check if enough time has passed since last restart
        last_restart = self.last_restart_time.get(service_name)
        if last_restart:
            time_since_restart = datetime.now() - last_restart
            if time_since_restart.total_seconds() < delay:
                return

        # Attempt restart
        self.logger.warning(
            f"Attempting to restart failed service {config.display_name} "
            f"(attempt {attempts + 1}/{config.max_restart_attempts})",
        )

        self.restart_attempts[service_name] = attempts + 1
        self.last_restart_time[service_name] = datetime.now()

        success = await self.restart_service(service_name)

        if success:
            self.logger.info(f"Successfully restarted {config.display_name}")
            # Reset attempt counter on successful restart
            self.restart_attempts[service_name] = 0
        else:
            self.logger.error(f"Failed to restart {config.display_name}")

        self.save_service_state()


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="PAKE+ Enhanced Service Manager")
    parser.add_argument(
        "command",
        choices=[
            "start",
            "stop",
            "restart",
            "status",
            "monitor",
            "start-all",
            "stop-all",
        ],
        help="Command to execute",
    )
    parser.add_argument("--service", help="Specific service name")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--force", action="store_true", help="Force operation")
    parser.add_argument("--interval", type=int, default=30, help="Monitoring interval")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    args = parser.parse_args()

    manager = PAKEServiceManager(args.config)

    if args.command == "start":
        if not args.service:
            print("--service required for start command")
            sys.exit(1)
        success = await manager.start_service(args.service, args.force)
        sys.exit(0 if success else 1)

    elif args.command == "stop":
        if not args.service:
            print("--service required for stop command")
            sys.exit(1)
        success = await manager.stop_service(args.service, args.force)
        sys.exit(0 if success else 1)

    elif args.command == "restart":
        if not args.service:
            print("--service required for restart command")
            sys.exit(1)
        success = await manager.restart_service(args.service)
        sys.exit(0 if success else 1)

    elif args.command == "start-all":
        success = await manager.start_all_services()
        sys.exit(0 if success else 1)

    elif args.command == "stop-all":
        success = await manager.stop_all_services()
        sys.exit(0 if success else 1)

    elif args.command == "status":
        status = await manager.get_system_status()

        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print(f"Overall Status: {status['overall_status'].upper()}")
            print(
                f"Services: {status['summary']['running']}/{
                    status['summary']['total']
                } running",
            )
            print("\nService Details:")
            for service_name, info in status["services"].items():
                state_icon = {
                    "running": "🟢",
                    "stopped": "🔴",
                    "failed": "❌",
                    "starting": "🟡",
                    "unknown": "❓",
                }.get(info["state"], "❓")
                criticality = "🔥" if info["critical"] else "ℹ️"
                print(
                    f"  {state_icon} {criticality} {info['display_name']}: {
                        info['state'].upper()
                    }",
                )
                if info["restart_attempts"] > 0:
                    print(f"    Restart attempts: {info['restart_attempts']}")

    elif args.command == "monitor":
        try:
            await manager.run_service_loop(args.interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
