#!/usr/bin/env python3
"""PAKE+ Command Line Interface
User-friendly wrapper for all PAKE+ system operations
Addresses all recurring deployment and management issues
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Color codes for terminal output


class Colors:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"

    @staticmethod
    def blue(text):
        return f"{Colors.BLUE}{text}{Colors.END}"

    @staticmethod
    def green(text):
        return f"{Colors.GREEN}{text}{Colors.END}"

    @staticmethod
    def yellow(text):
        return f"{Colors.YELLOW}{text}{Colors.END}"

    @staticmethod
    def red(text):
        return f"{Colors.RED}{text}{Colors.END}"

    @staticmethod
    def purple(text):
        return f"{Colors.PURPLE}{text}{Colors.END}"

    @staticmethod
    def cyan(text):
        return f"{Colors.CYAN}{text}{Colors.END}"

    @staticmethod
    def bold(text):
        return f"{Colors.BOLD}{text}{Colors.END}"


class PAKECommandLineInterface:
    """Main PAKE+ command line interface"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.scripts_dir = self.base_dir / "scripts"

        # Ensure we're in the right directory
        os.chdir(self.base_dir)

    def print_banner(self):
        """Print PAKE+ banner"""
        banner = f"""
{Colors.cyan("=" * 80)}
{Colors.bold(Colors.blue("PAKE+ System - Personal Autonomous Knowledge Engine Plus"))}
{Colors.green("Comprehensive deployment, management, and monitoring solution")}
{Colors.cyan("=" * 80)}
"""
        print(banner)

    def print_help(self):
        """Print comprehensive help"""
        help_text = f""" {Colors.bold("AVAILABLE COMMANDS:")}

{Colors.yellow("🚀 DEPLOYMENT COMMANDS")}
  {Colors.green("deploy")}           Full system deployment
  {Colors.green("quick-deploy")}     Quick deployment (skip optional components)
  {Colors.green("dev-deploy")}       Development environment deployment
  {Colors.green("prod-deploy")}      Production environment deployment

{Colors.yellow("⚙️  SERVICE MANAGEMENT")}
  {Colors.green("start")}            Start all services
  {Colors.green("stop")}             Stop all services
  {Colors.green("restart")}          Restart all services
  {Colors.green("status")}           Show service status
  {Colors.green("logs")}             View service logs
  {Colors.green("health")}           Check system health

{Colors.yellow("🔧 MAINTENANCE")}
  {Colors.green("update")}           Update system components
  {Colors.green("backup")}           Backup system data
  {Colors.green("restore")}          Restore from backup
  {Colors.green("clean")}            Clean temporary files
  {Colors.green("reset")}            Reset system (careful!)

{Colors.yellow("🧪 TESTING & VALIDATION")}
  {Colors.green("test")}             Run comprehensive system tests
  {Colors.green("validate")}         Validate system configuration
  {Colors.green("benchmark")}        Run performance benchmarks
  {Colors.green("security-scan")}    Run security scans

{Colors.yellow("📊 MONITORING & ANALYTICS")}
  {Colors.green("monitor")}          Start system monitoring
  {Colors.green("dashboard")}        Open system dashboard
  {Colors.green("report")}           Generate system reports
  {Colors.green("metrics")}          Show system metrics

{Colors.yellow("🛠️  DEVELOPMENT")}
  {Colors.green("dev")}              Start development environment
  {Colors.green("build")}            Build system components
  {Colors.green("lint")}             Run code quality checks
  {Colors.green("format")}           Format code

{Colors.yellow("ℹ️  INFORMATION")}
  {Colors.green("version")}          Show version information
  {Colors.green("info")}             Show system information
  {Colors.green("docs")}             Open documentation
  {Colors.green("troubleshoot")}     Troubleshooting guide

{Colors.bold("EXAMPLES:")}
  {Colors.cyan("python pake.py deploy")}                 # Full deployment
  {Colors.cyan("python pake.py start --service mcp_server")}    # Start specific service
  {Colors.cyan("python pake.py test --category integration")}   # Run integration tests
  {Colors.cyan("python pake.py status --json")}                 # JSON status output
  {
            Colors.cyan("python pake.py logs --follow")
        }                 # Follow logs in real-time

{Colors.bold("OPTIONS:")}
  {Colors.green("--help, -h")}       Show help message
  {Colors.green("--verbose, -v")}    Verbose output
  {Colors.green("--quiet, -q")}      Quiet output
  {Colors.green("--json")}           JSON output format
  {Colors.green("--force")}          Force operation
  {Colors.green("--dry-run")}        Show what would be done

For detailed help on any command: {Colors.cyan("python pake.py <command> --help")} """
        print(help_text)

    async def handle_command(self, args: argparse.Namespace) -> int:
        """Handle command execution"""
        command = args.command

        try:
            # Map commands to handlers
            command_handlers = {
                # Deployment commands
                "deploy": self._handle_deploy,
                "quick-deploy": self._handle_quick_deploy,
                "dev-deploy": self._handle_dev_deploy,
                "prod-deploy": self._handle_prod_deploy,
                # Service management
                "start": self._handle_start,
                "stop": self._handle_stop,
                "restart": self._handle_restart,
                "status": self._handle_status,
                "logs": self._handle_logs,
                "health": self._handle_health,
                # Maintenance
                "update": self._handle_update,
                "backup": self._handle_backup,
                "restore": self._handle_restore,
                "clean": self._handle_clean,
                "reset": self._handle_reset,
                # Testing
                "test": self._handle_test,
                "validate": self._handle_validate,
                "benchmark": self._handle_benchmark,
                "security-scan": self._handle_security_scan,
                # Monitoring
                "monitor": self._handle_monitor,
                "dashboard": self._handle_dashboard,
                "report": self._handle_report,
                "metrics": self._handle_metrics,
                # Development
                "dev": self._handle_dev,
                "build": self._handle_build,
                "lint": self._handle_lint,
                "format": self._handle_format,
                # Information
                "version": self._handle_version,
                "info": self._handle_info,
                "docs": self._handle_docs,
                "troubleshoot": self._handle_troubleshoot,
            }

            if command in command_handlers:
                return await command_handlers[command](args)
            print(f"{Colors.red('❌ Unknown command:')} {command}")
            return 1

        except KeyboardInterrupt:
            print(f"\n{Colors.yellow('🛑 Operation cancelled by user')}")
            return 130
        except Exception as e:
            print(f"{Colors.red('💥 Error:')} {str(e)}")
            if args.verbose:
                import traceback

                traceback.print_exc()
            return 1

    # Deployment Commands
    async def _handle_deploy(self, args: argparse.Namespace) -> int:
        """Handle full deployment"""
        print(f"{Colors.blue('🚀 Starting PAKE+ Full Deployment...')}")

        try:
            from unified_deployment import (
                DeploymentConfig,
                DeploymentMode,
                PAKEUnifiedDeployment,
            )

            config = DeploymentConfig(
                mode=(
                    DeploymentMode.DEVELOPMENT
                    if args.dev
                    else DeploymentMode.PRODUCTION
                ),
                skip_docker=args.skip_docker,
                skip_dependencies=args.skip_deps,
                skip_frontend=args.skip_frontend,
                force_reinstall=args.force,
                timeout_multiplier=args.timeout_multiplier,
            )

            deployment = PAKEUnifiedDeployment(config)
            success = await deployment.execute_full_deployment()

            if success:
                print(f"{Colors.green('✅ Deployment completed successfully!')}")
                self._print_post_deployment_info()
                return 0
            print(f"{Colors.red('❌ Deployment failed!')}")
            return 1

        except ImportError:
            return await self._fallback_deploy(args)
        except Exception as e:
            print(f"{Colors.red('💥 Deployment error:')} {str(e)}")
            return 1

    async def _handle_quick_deploy(self, args: argparse.Namespace) -> int:
        """Handle quick deployment"""
        print(f"{Colors.blue('⚡ Starting PAKE+ Quick Deployment...')}")

        # Set quick deployment flags
        args.skip_frontend = True
        args.skip_deps = getattr(args, "skip_deps", False)

        return await self._handle_deploy(args)

    async def _handle_dev_deploy(self, args: argparse.Namespace) -> int:
        """Handle development deployment"""
        print(f"{Colors.blue('🛠️ Starting PAKE+ Development Deployment...')}")

        args.dev = True
        return await self._handle_deploy(args)

    async def _handle_prod_deploy(self, args: argparse.Namespace) -> int:
        """Handle production deployment"""
        print(f"{Colors.blue('🏭 Starting PAKE+ Production Deployment...')}")

        args.dev = False
        return await self._handle_deploy(args)

    # Service Management Commands
    async def _handle_start(self, args: argparse.Namespace) -> int:
        """Handle service start"""
        try:
            from enhanced_service_manager import PAKEServiceManager

            manager = PAKEServiceManager()

            if args.service:
                print(f"{Colors.blue('🚀 Starting service:')} {args.service}")
                success = await manager.start_service(args.service, args.force)
            else:
                print(f"{Colors.blue('🚀 Starting all services...')}")
                success = await manager.start_all_services()

            if success:
                print(f"{Colors.green('✅ Service(s) started successfully')}")
                return 0
            print(f"{Colors.red('❌ Failed to start service(s)')}")
            return 1

        except ImportError:
            return await self._fallback_service_command("start", args)
        except Exception as e:
            print(f"{Colors.red('💥 Start error:')} {str(e)}")
            return 1

    async def _handle_stop(self, args: argparse.Namespace) -> int:
        """Handle service stop"""
        try:
            from enhanced_service_manager import PAKEServiceManager

            manager = PAKEServiceManager()

            if args.service:
                print(f"{Colors.blue('🛑 Stopping service:')} {args.service}")
                success = await manager.stop_service(args.service, args.force)
            else:
                print(f"{Colors.blue('🛑 Stopping all services...')}")
                success = await manager.stop_all_services()

            if success:
                print(f"{Colors.green('✅ Service(s) stopped successfully')}")
                return 0
            print(f"{Colors.red('❌ Failed to stop service(s)')}")
            return 1

        except ImportError:
            return await self._fallback_service_command("stop", args)
        except Exception as e:
            print(f"{Colors.red('💥 Stop error:')} {str(e)}")
            return 1

    async def _handle_restart(self, args: argparse.Namespace) -> int:
        """Handle service restart"""
        try:
            from enhanced_service_manager import PAKEServiceManager

            manager = PAKEServiceManager()

            if args.service:
                print(f"{Colors.blue('🔄 Restarting service:')} {args.service}")
                success = await manager.restart_service(args.service)
            else:
                print(f"{Colors.blue('🔄 Restarting all services...')}")
                await manager.stop_all_services()
                await asyncio.sleep(5)
                success = await manager.start_all_services()

            if success:
                print(f"{Colors.green('✅ Service(s) restarted successfully')}")
                return 0
            print(f"{Colors.red('❌ Failed to restart service(s)')}")
            return 1

        except ImportError:
            return await self._fallback_service_command("restart", args)
        except Exception as e:
            print(f"{Colors.red('💥 Restart error:')} {str(e)}")
            return 1

    async def _handle_status(self, args: argparse.Namespace) -> int:
        """Handle status check"""
        try:
            from enhanced_service_manager import PAKEServiceManager

            manager = PAKEServiceManager()
            status = await manager.get_system_status()

            if args.json:
                print(json.dumps(status, indent=2))
            else:
                self._print_status(status)

            return 0

        except ImportError:
            return await self._fallback_status(args)
        except Exception as e:
            print(f"{Colors.red('💥 Status error:')} {str(e)}")
            return 1

    async def _handle_logs(self, args: argparse.Namespace) -> int:
        """Handle log viewing"""
        logs_dir = self.base_dir / "logs"

        if not logs_dir.exists():
            print(f"{Colors.red('❌ Logs directory not found')}")
            return 1

        if args.follow:
            # Follow logs in real-time
            print(f"{Colors.blue('📄 Following logs (Ctrl+C to stop)...')}")

            try:
                # Find most recent log file
                log_files = list(logs_dir.glob("*.log"))
                if not log_files:
                    print(f"{Colors.red('❌ No log files found')}")
                    return 1

                latest_log = max(log_files, key=lambda f: f.stat().st_mtime)

                # Use tail -f equivalent
                process = await asyncio.create_subprocess_exec(
                    "tail",
                    "-f",
                    str(latest_log),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    print(line.decode().rstrip())

            except KeyboardInterrupt:
                print(f"\n{Colors.yellow('📄 Log following stopped')}")
                return 0
        else:
            # Show recent logs
            print(f"{Colors.blue('📄 Recent log files:')}")

            log_files = sorted(
                logs_dir.glob("*.log"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )

            for i, log_file in enumerate(log_files[:5]):
                size_mb = log_file.stat().st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

                print(
                    f"  {i + 1}. {log_file.name} ({size_mb:.1f}MB, {mtime.strftime('%Y-%m-%d %H:%M:%S')})",
                )

            if args.service:
                # Show specific service logs
                service_logs = [f for f in log_files if args.service in f.name]
                if service_logs:
                    latest = service_logs[0]
                    print(f"\n{Colors.blue(f'📄 Latest logs for {args.service}:')}")

                    with open(latest) as f:
                        lines = f.readlines()
                        # Show last 20 lines
                        for line in lines[-20:]:
                            print(line.rstrip())

        return 0

    async def _handle_health(self, args: argparse.Namespace) -> int:
        """Handle health check"""
        try:
            from service_health_monitor import PAKEServiceMonitor

            monitor = PAKEServiceMonitor()

            if args.service:
                result = await monitor.check_service_health(args.service)

                if args.json:
                    print(
                        json.dumps(
                            {
                                "service": args.service,
                                "status": result.status.value,
                                "response_time_ms": result.response_time_ms,
                                "error": result.error_message,
                                "timestamp": result.timestamp.isoformat(),
                            },
                            indent=2,
                        ),
                    )
                else:
                    status_icon = monitor._get_status_icon(result.status)
                    print(f"{status_icon} {args.service}: {result.status.value}")
                    if result.error_message:
                        print(f"  Error: {result.error_message}")
            else:
                results = await monitor.check_all_services()

                if args.json:
                    output = {"timestamp": datetime.now().isoformat(), "services": {}}

                    for service_name, result in results.items():
                        output["services"][service_name] = {
                            "status": result.status.value,
                            "response_time_ms": result.response_time_ms,
                            "error": result.error_message,
                        }

                    print(json.dumps(output, indent=2))
                else:
                    print(f"{Colors.blue('🏥 System Health Check:')}")

                    for service_name, result in results.items():
                        status_icon = monitor._get_status_icon(result.status)
                        print(
                            f"  {status_icon} {service_name}: {result.status.value} ({result.response_time_ms:.1f}ms)",
                        )

                        if result.error_message:
                            print(f"    ⚠️  {result.error_message}")

            return 0

        except ImportError:
            return await self._fallback_health(args)
        except Exception as e:
            print(f"{Colors.red('💥 Health check error:')} {str(e)}")
            return 1

    # Testing Commands
    async def _handle_test(self, args: argparse.Namespace) -> int:
        """Handle testing"""
        try:
            from comprehensive_system_test import PAKESystemTestSuite

            print(f"{Colors.blue('🧪 Running PAKE+ System Tests...')}")

            test_config = {
                "parallel_tests": not args.sequential,
                "skip_slow_tests": args.skip_slow,
                "timeout_multiplier": getattr(args, "timeout_multiplier", 1.0),
            }

            if hasattr(args, "category") and args.category:
                print(f"{Colors.blue(f'📂 Running {args.category} tests only...')}")

            test_suite = PAKESystemTestSuite(test_config)
            results = await test_suite.run_all_tests()

            if args.json:
                print(json.dumps(results, indent=2))

            return 0 if results["overall_success"] else 1

        except ImportError:
            print(f"{Colors.red('❌ Test suite not available')}")
            return 1
        except Exception as e:
            print(f"{Colors.red('💥 Test error:')} {str(e)}")
            return 1

    async def _handle_validate(self, args: argparse.Namespace) -> int:
        """Handle validation"""
        print(f"{Colors.blue('✅ Validating PAKE+ system configuration...')}")

        validation_checks = [
            ("Docker availability", self._validate_docker),
            ("Directory structure", self._validate_directories),
            ("Configuration files", self._validate_config_files),
            ("Network ports", self._validate_ports),
            ("Permissions", self._validate_permissions),
        ]

        results = []

        for check_name, check_function in validation_checks:
            print(f"  Checking {check_name}...")

            try:
                success, message = await check_function()
                results.append(success)

                if success:
                    print(f"    ✅ {message}")
                else:
                    print(f"    ❌ {message}")

            except Exception as e:
                print(f"    💥 {check_name} failed: {e}")
                results.append(False)

        success_count = sum(results)
        total_count = len(results)

        if success_count == total_count:
            print(
                f"\n{Colors.green('✅ All validations passed!')} ({success_count}/{total_count})",
            )
            return 0
        print(
            f"\n{Colors.red('❌ Some validations failed!')} ({success_count}/{total_count})",
        )
        return 1

    # Information Commands
    async def _handle_version(self, args: argparse.Namespace) -> int:
        """Handle version display"""
        version_info = {
            "pake_version": "2.0.0",
            "build_date": "2025-09-02",
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
        }

        if args.json:
            print(json.dumps(version_info, indent=2))
        else:
            print(
                f"""
{Colors.bold("PAKE+ System Version Information")}
{Colors.cyan("=" * 40)}
PAKE+ Version: {Colors.green(version_info["pake_version"])}
Build Date: {Colors.green(version_info["build_date"])}
Python Version: {Colors.green(version_info["python_version"])}
Platform: {Colors.green(version_info["platform"])}
{Colors.cyan("=" * 40)}
""",
            )

        return 0

    async def _handle_info(self, args: argparse.Namespace) -> int:
        """Handle system info display"""
        info = {
            "base_directory": str(self.base_dir),
            "scripts_directory": str(self.scripts_dir),
            "vault_path": os.environ.get("VAULT_PATH", str(self.base_dir / "vault")),
            "python_executable": sys.executable,
            "environment": {
                "NODE_ENV": os.environ.get("NODE_ENV", "not set"),
                "PAKE_MODE": os.environ.get("PAKE_MODE", "not set"),
            },
        }

        if args.json:
            print(json.dumps(info, indent=2))
        else:
            print(
                f"""
{Colors.bold("PAKE+ System Information")}
{Colors.cyan("=" * 50)}
Base Directory: {Colors.green(info["base_directory"])}
Scripts Directory: {Colors.green(info["scripts_directory"])}
Vault Path: {Colors.green(info["vault_path"])}
Python Executable: {Colors.green(info["python_executable"])}

Environment Variables:
  NODE_ENV: {Colors.green(info["environment"]["NODE_ENV"])}
  PAKE_MODE: {Colors.green(info["environment"]["PAKE_MODE"])}
{Colors.cyan("=" * 50)}
""",
            )

        return 0

    async def _handle_docs(self, args: argparse.Namespace) -> int:
        """Handle documentation"""
        docs_files = [
            "README.md",
            "COMPLETE_AUTOMATION_GUIDE.md",
            "ENHANCED_MCP_IMPLEMENTATION_GUIDE.md",
            "QUICK_START_AUTOMATION.md",
        ]

        print(f"{Colors.blue('📚 Available Documentation:')}")

        for i, doc_file in enumerate(docs_files, 1):
            doc_path = self.base_dir / doc_file
            if doc_path.exists():
                size_kb = doc_path.stat().st_size / 1024
                print(f"  {i}. {doc_file} ({size_kb:.1f}KB)")
            else:
                print(f"  {i}. {doc_file} (not found)")

        return 0

    async def _handle_troubleshoot(self, args: argparse.Namespace) -> int:
        """Handle troubleshooting guide"""
        troubleshoot_guide = f"""
{Colors.bold("🔧 PAKE+ Troubleshooting Guide")}
{Colors.cyan("=" * 50)}

{Colors.yellow("Common Issues and Solutions:")}

1. {Colors.bold("Docker services not starting")}
   • Check Docker Desktop is running
   • Run: docker ps
   • Try: docker-compose down && docker-compose up -d

2. {Colors.bold("Port already in use errors")}
   • Check what's using the port: netstat -an | grep <port>
   • Stop conflicting services
   • Modify port configuration in docker-compose.yml

3. {Colors.bold("Permission denied errors")}
   • Check file permissions: ls -la
   • Fix with: chmod +x scripts/*
   • Run with appropriate privileges

4. {Colors.bold("Python import errors")}
   • Check Python path: echo $PYTHONPATH
   • Install dependencies: pip install -r requirements.txt
   • Use virtual environment

5. {Colors.bold("Database connection issues")}
   • Check PostgreSQL is running: docker ps | grep postgres
   • Verify credentials in .env file
   • Check database logs: docker logs pake_postgres

6. {Colors.bold("Frontend not loading")}
   • Check Node.js version: node --version
   • Install dependencies: cd frontend && npm install
   • Start dev server: npm run dev

{Colors.yellow("Diagnostic Commands:")}
  {Colors.green("python pake.py status")}        # Check system status
  {Colors.green("python pake.py health")}        # Health check all services
  {Colors.green("python pake.py validate")}      # Validate configuration
  {Colors.green("python pake.py test")}          # Run system tests
  {Colors.green("python pake.py logs")}          # View system logs

{Colors.yellow("Quick Fixes:")}
  {Colors.green("python pake.py clean")}         # Clean temporary files
  {Colors.green("python pake.py restart")}       # Restart all services
  {Colors.green("python pake.py deploy --force")} # Force redeploy

{Colors.yellow("Get Help:")}
  • Check logs in the logs/ directory
  • Review error messages carefully
  • Try running with --verbose flag
  • Create issue at: https://github.com/pake-system/issues

{Colors.cyan("=" * 50)}
"""
        print(troubleshoot_guide)
        return 0

    # Fallback methods for when modules aren't available
    async def _fallback_deploy(self, args: argparse.Namespace) -> int:
        """Fallback deployment method"""
        print(f"{Colors.yellow('⚠️  Using fallback deployment method...')}")

        try:
            deploy_script = self.scripts_dir / "deploy_pake.py"
            if deploy_script.exists():
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(deploy_script),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await process.communicate()

                print(stdout.decode())
                if stderr:
                    print(f"{Colors.red('Errors:')}")
                    print(stderr.decode())

                return process.returncode
            print(f"{Colors.red('❌ Deployment script not found')}")
            return 1

        except Exception as e:
            print(f"{Colors.red('💥 Fallback deployment failed:')} {str(e)}")
            return 1

    async def _fallback_service_command(
        self,
        command: str,
        args: argparse.Namespace,
    ) -> int:
        """Fallback service command"""
        print(f"{Colors.yellow(f'⚠️  Using fallback {command} method...')}")

        if command == "start":
            # Try Docker Compose
            try:
                process = await asyncio.create_subprocess_exec(
                    "docker-compose",
                    "-f",
                    str(self.base_dir / "docker" / "docker-compose.yml"),
                    "up",
                    "-d",
                    cwd=self.base_dir / "docker",
                )

                return_code = await process.wait()

                if return_code == 0:
                    print(f"{Colors.green('✅ Services started via Docker Compose')}")
                else:
                    print(
                        f"{Colors.red('❌ Failed to start services via Docker Compose')}",
                    )

                return return_code

            except Exception as e:
                print(f"{Colors.red('💥 Fallback start failed:')} {str(e)}")
                return 1

        elif command == "stop":
            try:
                process = await asyncio.create_subprocess_exec(
                    "docker-compose",
                    "-f",
                    str(self.base_dir / "docker" / "docker-compose.yml"),
                    "down",
                    cwd=self.base_dir / "docker",
                )

                return_code = await process.wait()

                if return_code == 0:
                    print(f"{Colors.green('✅ Services stopped via Docker Compose')}")
                else:
                    print(
                        f"{Colors.red('❌ Failed to stop services via Docker Compose')}",
                    )

                return return_code

            except Exception as e:
                print(f"{Colors.red('💥 Fallback stop failed:')} {str(e)}")
                return 1

        return 1

    async def _fallback_status(self, args: argparse.Namespace) -> int:
        """Fallback status check"""
        print(f"{Colors.yellow('⚠️  Using fallback status check...')}")

        try:
            process = await asyncio.create_subprocess_exec(
                "docker-compose",
                "-f",
                str(self.base_dir / "docker" / "docker-compose.yml"),
                "ps",
                cwd=self.base_dir / "docker",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode()
                print(f"{Colors.blue('📊 Docker Compose Status:')}")
                print(output)
            else:
                print(f"{Colors.red('❌ Failed to get status')}")
                if stderr:
                    print(stderr.decode())

            return process.returncode

        except Exception as e:
            print(f"{Colors.red('💥 Fallback status failed:')} {str(e)}")
            return 1

    async def _fallback_health(self, args: argparse.Namespace) -> int:
        """Fallback health check"""
        print(f"{Colors.yellow('⚠️  Using basic health check...')}")

        services_to_check = [
            ("PostgreSQL", "localhost", 5432),
            ("Redis", "localhost", 6379),
            ("MCP Server", "localhost", 8000),
            ("API Bridge", "localhost", 3000),
        ]

        for service_name, host, port in services_to_check:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=5,
                )
                writer.close()
                await writer.wait_closed()

                print(f"  {Colors.green('✅')} {service_name}: Running")

            except Exception:
                print(f"  {Colors.red('❌')} {service_name}: Not accessible")

        return 0

    # Validation helper methods
    async def _validate_docker(self) -> tuple:
        """Validate Docker availability"""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)

            if process.returncode == 0:
                version = stdout.decode().strip()
                return True, f"Docker available: {version}"
            return False, "Docker not available"

        except Exception as e:
            return False, f"Docker check failed: {str(e)}"

    async def _validate_directories(self) -> tuple:
        """Validate directory structure"""
        required_dirs = ["scripts", "docker", "vault", "logs", "data"]
        missing_dirs = []

        for dir_name in required_dirs:
            if not (self.base_dir / dir_name).exists():
                missing_dirs.append(dir_name)

        if missing_dirs:
            return False, f"Missing directories: {', '.join(missing_dirs)}"
        return True, f"All {len(required_dirs)} directories exist"

    async def _validate_config_files(self) -> tuple:
        """Validate configuration files"""
        required_files = ["docker/docker-compose.yml", ".env.example"]

        missing_files = []

        for file_path in required_files:
            if not (self.base_dir / file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            return False, f"Missing config files: {', '.join(missing_files)}"
        return True, "All configuration files exist"

    async def _validate_ports(self) -> tuple:
        """Validate network ports"""
        ports_to_check = [5432, 6379, 8000, 3000]
        busy_ports = []

        for port in ports_to_check:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection("localhost", port),
                    timeout=1,
                )
                writer.close()
                await writer.wait_closed()
                busy_ports.append(port)

            except BaseException:
                pass  # Port is free

        if busy_ports:
            return True, f"Services running on ports: {', '.join(map(str, busy_ports))}"
        return True, "All required ports are free"

    async def _validate_permissions(self) -> tuple:
        """Validate file permissions"""
        try:
            test_file = self.base_dir / f".pake_permission_test_{int(time.time())}"
            test_file.write_text("test")
            test_file.unlink()

            return True, "File permissions OK"

        except Exception as e:
            return False, f"Permission issue: {str(e)}"

    # Helper methods
    def _print_status(self, status: dict[str, Any]):
        """Print formatted status"""
        print(f"{Colors.blue('📊 PAKE+ System Status')}")
        print(
            f"Overall Status: {self._format_status(status.get('overall_status', 'unknown'))}",
        )

        if "services" in status:
            print(f"\n{Colors.bold('Services:')}")

            for service_name, info in status["services"].items():
                state_icons = {
                    "running": "🟢",
                    "stopped": "🔴",
                    "failed": "❌",
                    "starting": "🟡",
                    "unknown": "❓",
                }

                icon = state_icons.get(info.get("state", "unknown"), "❓")
                criticality = "🔥" if info.get("critical", False) else "ℹ️"

                print(
                    f"  {icon} {criticality} {info.get('display_name', service_name)}: {info.get('state', 'unknown').upper()}",
                )

                if info.get("restart_attempts", 0) > 0:
                    print(f"    Restart attempts: {info['restart_attempts']}")

    def _format_status(self, status: str) -> str:
        """Format status with color"""
        color_map = {
            "healthy": Colors.green,
            "running": Colors.green,
            "degraded": Colors.yellow,
            "unhealthy": Colors.red,
            "critical": Colors.red,
            "unknown": Colors.yellow,
        }

        color_func = color_map.get(status.lower(), Colors.white)
        return color_func(status.upper())

    def _print_post_deployment_info(self):
        """Print post-deployment information"""
        info = f""" {Colors.green("🎉 PAKE+ System Ready!")}

{Colors.bold("Service Endpoints:")}
  • MCP Server: {Colors.cyan("http://localhost:8000")}
  • API Bridge: {Colors.cyan("http://localhost:3000")}
  • n8n Automation: {Colors.cyan("http://localhost:5678")}
  • Frontend: {Colors.cyan("http://localhost:3001")}

{Colors.bold("Next Steps:")}
  1. Check service health: {Colors.cyan("python pake.py health")}
  2. Run system tests: {Colors.cyan("python pake.py test")}
  3. Start monitoring: {Colors.cyan("python pake.py monitor")}
  4. Open documentation: {Colors.cyan("python pake.py docs")}

{Colors.bold("Management Commands:")}
  • View status: {Colors.cyan("python pake.py status")}
  • Follow logs: {Colors.cyan("python pake.py logs --follow")}
  • Restart services: {Colors.cyan("python pake.py restart")}

{Colors.yellow("💡 Tip:")} Use {Colors.cyan("python pake.py --help")}
                                  for all available commands
"""
        print(info)

    # Placeholder methods for unimplemented commands
    async def _handle_update(self, args) -> int:
        print(f"{Colors.yellow('🔄 Update functionality coming soon...')}")
        return 0

    async def _handle_backup(self, args) -> int:
        print(f"{Colors.yellow('💾 Backup functionality coming soon...')}")
        return 0

    async def _handle_restore(self, args) -> int:
        print(f"{Colors.yellow('📥 Restore functionality coming soon...')}")
        return 0

    async def _handle_clean(self, args) -> int:
        print(f"{Colors.blue('🧹 Cleaning temporary files...')}")

        temp_patterns = [
            ".pake_*",
            "__pycache__",
            "*.pyc",
            ".pytest_cache",
            "node_modules/.cache",
            "logs/*.log.old",
        ]

        cleaned_count = 0

        for pattern in temp_patterns:
            for file_path in self.base_dir.rglob(pattern):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        cleaned_count += 1
                    elif file_path.is_dir():
                        import shutil

                        shutil.rmtree(file_path)
                        cleaned_count += 1
                except Exception:
                    pass

        print(
            f"{Colors.green(f'✅ Cleaned {cleaned_count} temporary files/directories')}",
        )
        return 0

    async def _handle_reset(self, args) -> int:
        if not args.force:
            response = input(
                f"{Colors.red('⚠️  This will reset the entire system. Continue? (y/N): ')}",
            )
            if response.lower() != "y":
                print("Reset cancelled.")
                return 0

        print(f"{Colors.red('🔄 Resetting PAKE+ system...')}")
        print(
            f"{Colors.yellow('⚠️  Reset functionality not yet implemented for safety')}",
        )
        return 0

    async def _handle_benchmark(self, args) -> int:
        print(f"{Colors.yellow('📈 Benchmark functionality coming soon...')}")
        return 0

    async def _handle_security_scan(self, args) -> int:
        print(f"{Colors.yellow('🛡️  Security scan functionality coming soon...')}")
        return 0

    async def _handle_monitor(self, args) -> int:
        print(f"{Colors.yellow('📊 Monitor functionality coming soon...')}")
        return 0

    async def _handle_dashboard(self, args) -> int:
        print(f"{Colors.yellow('📈 Dashboard functionality coming soon...')}")
        return 0

    async def _handle_report(self, args) -> int:
        print(f"{Colors.yellow('📋 Report functionality coming soon...')}")
        return 0

    async def _handle_metrics(self, args) -> int:
        print(f"{Colors.yellow('📊 Metrics functionality coming soon...')}")
        return 0

    async def _handle_dev(self, args) -> int:
        print(f"{Colors.yellow('🛠️  Development mode coming soon...')}")
        return 0

    async def _handle_build(self, args) -> int:
        print(f"{Colors.yellow('🔨 Build functionality coming soon...')}")
        return 0

    async def _handle_lint(self, args) -> int:
        print(f"{Colors.yellow('🔍 Lint functionality coming soon...')}")
        return 0

    async def _handle_format(self, args) -> int:
        print(f"{Colors.yellow('✨ Format functionality coming soon...')}")
        return 0


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        description="PAKE+ System - Personal Autonomous Knowledge Engine Plus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "command",
        nargs="?",
        help="Command to execute (see --help for list)",
    )

    # Global options
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet output")
    parser.add_argument("--json", action="store_true", help="JSON output format")
    parser.add_argument("--force", action="store_true", help="Force operation")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done",
    )

    # Deployment options
    parser.add_argument("--dev", action="store_true", help="Development mode")
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Skip Docker deployment",
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
        "--timeout-multiplier",
        type=float,
        default=1.0,
        help="Timeout multiplier",
    )

    # Service options
    parser.add_argument("--service", help="Specific service name")

    # Log options
    parser.add_argument(
        "--follow",
        action="store_true",
        help="Follow logs in real-time",
    )

    # Test options
    parser.add_argument("--category", help="Test category to run")
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run tests sequentially",
    )
    parser.add_argument("--skip-slow", action="store_true", help="Skip slow tests")

    return parser


async def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()

    cli = PAKECommandLineInterface()

    # Handle special cases
    if not args.command or args.command == "help":
        cli.print_banner()
        cli.print_help()
        return 0

    # Set logging level
    if args.quiet:
        import logging

        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    # Execute command
    try:
        return await cli.handle_command(args)
    except Exception as e:
        print(f"{Colors.red('💥 Fatal error:')} {str(e)}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.yellow('🛑 Interrupted by user')}")
        sys.exit(130)
    except Exception as e:
        print(f"{Colors.red('💥 Fatal error:')} {str(e)}")
        sys.exit(1)
