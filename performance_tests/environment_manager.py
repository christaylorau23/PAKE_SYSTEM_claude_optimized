"""
PAKE System Performance Testing Environment Configuration
========================================================

This module provides configuration and utilities for setting up
dedicated performance testing environments that mirror production
architecture but with scaled-down resources.

Key Features:
- Environment provisioning scripts
- Performance baseline establishment
- Automated test execution
- Results analysis and reporting
"""

import os
import json
import time
import subprocess
import docker
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PerformanceEnvironmentConfig:
    """Configuration for performance testing environment"""
    name: str
    base_url: str
    database_url: str
    redis_url: str
    max_concurrent_users: int
    test_duration_minutes: int
    resource_limits: Dict[str, Any]
    monitoring_enabled: bool = True
    cleanup_after_test: bool = True


class PerformanceEnvironmentManager:
    """Manages performance testing environments"""

    def __init__(self, config_path: str = "performance_tests/config/environments.json"):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.docker_client = docker.from_env()
        self.environments: Dict[str, PerformanceEnvironmentConfig] = {}
        self.load_configurations()

    def load_configurations(self):
        """Load environment configurations from file"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                configs = json.load(f)
                for name, config in configs.items():
                    self.environments[name] = PerformanceEnvironmentConfig(**config)
        else:
            self.create_default_configurations()

    def create_default_configurations(self):
        """Create default environment configurations"""
        default_configs = {
            "local": {
                "name": "local",
                "base_url": "http://localhost:8000",
                "database_url": "postgresql://test_user:test_password@localhost:5432/pake_perf_test",
                "redis_url": "redis://localhost:6379/2",
                "max_concurrent_users": 50,
                "test_duration_minutes": 5,
                "resource_limits": {
                    "cpu": "2",
                    "memory": "4Gi",
                    "disk": "10Gi"
                },
                "monitoring_enabled": True,
                "cleanup_after_test": True
            },
            "staging": {
                "name": "staging",
                "base_url": "https://staging.pake-system.com",
                "database_url": "postgresql://staging_user:staging_password@staging-db:5432/pake_staging",
                "redis_url": "redis://staging-redis:6379/0",
                "max_concurrent_users": 200,
                "test_duration_minutes": 15,
                "resource_limits": {
                    "cpu": "4",
                    "memory": "8Gi",
                    "disk": "50Gi"
                },
                "monitoring_enabled": True,
                "cleanup_after_test": False
            },
            "production": {
                "name": "production",
                "base_url": "https://pake-system.com",
                "database_url": "postgresql://prod_user:prod_password@prod-db:5432/pake_production",
                "redis_url": "redis://prod-redis:6379/0",
                "max_concurrent_users": 1000,
                "test_duration_minutes": 30,
                "resource_limits": {
                    "cpu": "8",
                    "memory": "16Gi",
                    "disk": "100Gi"
                },
                "monitoring_enabled": True,
                "cleanup_after_test": False
            }
        }

        with open(self.config_path, 'w') as f:
            json.dump(default_configs, f, indent=2)

        # Reload configurations
        self.load_configurations()

    def provision_environment(self, env_name: str) -> bool:
        """Provision a performance testing environment"""
        if env_name not in self.environments:
            raise ValueError(f"Environment '{env_name}' not found")

        config = self.environments[env_name]
        print(f"Provisioning environment: {config.name}")

        try:
            # Start required services
            self._start_database(config)
            self._start_redis(config)
            self._start_application(config)

            # Wait for services to be ready
            self._wait_for_services(config)

            # Run health checks
            if not self._run_health_checks(config):
                raise Exception("Health checks failed")

            print(f"Environment '{env_name}' provisioned successfully")
            return True

        except Exception as e:
            print(f"Failed to provision environment '{env_name}': {e}")
            return False

    def _start_database(self, config: PerformanceEnvironmentConfig):
        """Start database service"""
        if config.name == "local":
            # Start local PostgreSQL container
            try:
                container = self.docker_client.containers.run(
                    "postgres:16-alpine",
                    name="pake-perf-db",
                    environment={
                        "POSTGRES_USER": "test_user",
                        "POSTGRES_PASSWORD": "test_password",
                        "POSTGRES_DB": "pake_perf_test"
                    },
                    ports={"5432": "5432"},
                    detach=True,
                    remove=True
                )
                print("PostgreSQL container started")
            except docker.errors.ContainerError:
                print("PostgreSQL container already running")

    def _start_redis(self, config: PerformanceEnvironmentConfig):
        """Start Redis service"""
        if config.name == "local":
            try:
                container = self.docker_client.containers.run(
                    "redis:7-alpine",
                    name="pake-perf-redis",
                    ports={"6379": "6379"},
                    detach=True,
                    remove=True
                )
                print("Redis container started")
            except docker.errors.ContainerError:
                print("Redis container already running")

    def _start_application(self, config: PerformanceEnvironmentConfig):
        """Start application service"""
        if config.name == "local":
            # Set environment variables
            env_vars = {
                "DATABASE_URL": config.database_url,
                "REDIS_URL": config.redis_url,
                "SECRET_KEY": "perf-test-secret-key",
                "USE_VAULT": "false"
            }

            # Start application
            try:
                subprocess.Popen([
                    "python", "-m", "uvicorn",
                    "src.pake_system.auth.example_app:app",
                    "--host", "0.0.0.0",
                    "--port", "8000"
                ], env={**os.environ, **env_vars})
                print("Application started")
            except Exception as e:
                print(f"Failed to start application: {e}")

    def _wait_for_services(self, config: PerformanceEnvironmentConfig, timeout: int = 60):
        """Wait for services to be ready"""
        print("Waiting for services to be ready...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                import requests
                response = requests.get(f"{config.base_url}/health", timeout=5)
                if response.status_code == 200:
                    print("Services are ready")
                    return True
            except:
                pass

            time.sleep(2)

        raise Exception("Services failed to start within timeout")

    def _run_health_checks(self, config: PerformanceEnvironmentConfig) -> bool:
        """Run comprehensive health checks"""
        print("Running health checks...")

        try:
            import requests

            # Basic health check
            response = requests.get(f"{config.base_url}/health", timeout=10)
            if response.status_code != 200:
                print(f"Health check failed: {response.status_code}")
                return False

            # Authentication check
            auth_response = requests.post(
                f"{config.base_url}/token",
                data={"username": "admin", "password": "secret"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            if auth_response.status_code != 200:
                print(f"Authentication check failed: {auth_response.status_code}")
                return False

            print("All health checks passed")
            return True

        except Exception as e:
            print(f"Health check error: {e}")
            return False

    def cleanup_environment(self, env_name: str):
        """Clean up environment after testing"""
        if env_name not in self.environments:
            return

        config = self.environments[env_name]

        if config.cleanup_after_test and config.name == "local":
            print(f"Cleaning up environment: {env_name}")

            # Stop containers
            try:
                containers = ["pake-perf-db", "pake-perf-redis"]
                for container_name in containers:
                    try:
                        container = self.docker_client.containers.get(container_name)
                        container.stop()
                        print(f"Stopped container: {container_name}")
                    except docker.errors.NotFound:
                        pass
            except Exception as e:
                print(f"Cleanup error: {e}")


class PerformanceTestRunner:
    """Runs performance tests against configured environments"""

    def __init__(self, env_manager: PerformanceEnvironmentManager):
        self.env_manager = env_manager
        self.results_dir = Path("performance_tests/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run_smoke_test(self, env_name: str = "local") -> Dict[str, Any]:
        """Run smoke test for CI/CD pipeline"""
        print(f"Running smoke test on {env_name}")

        config = self.env_manager.environments[env_name]

        # Provision environment
        if not self.env_manager.provision_environment(env_name):
            return {"success": False, "error": "Environment provisioning failed"}

        try:
            # Run smoke test
            cmd = [
                "locust",
                "-f", "performance_tests/locustfile.py",
                "--host", config.base_url,
                "--users", "10",
                "--spawn-rate", "2",
                "--run-time", "60s",
                "--headless",
                "--html", str(self.results_dir / f"smoke_test_{env_name}_{int(time.time())}.html")
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            # Parse results
            results = self._parse_locust_output(result.stdout)
            results["test_type"] = "smoke"
            results["environment"] = env_name
            results["success"] = result.returncode == 0

            # Save results
            self._save_results(results, f"smoke_test_{env_name}")

            return results

        except Exception as e:
            return {"success": False, "error": str(e)}

        finally:
            # Cleanup
            self.env_manager.cleanup_environment(env_name)

    def run_load_test(self, env_name: str = "staging", scenario: str = "normal") -> Dict[str, Any]:
        """Run comprehensive load test"""
        print(f"Running {scenario} load test on {env_name}")

        config = self.env_manager.environments[env_name]

        # Provision environment
        if not self.env_manager.provision_environment(env_name):
            return {"success": False, "error": "Environment provisioning failed"}

        try:
            # Determine test parameters based on scenario
            test_params = self._get_scenario_params(scenario, config)

            # Run load test
            cmd = [
                "locust",
                "-f", "performance_tests/locustfile.py",
                "--host", config.base_url,
                "--users", str(test_params["users"]),
                "--spawn-rate", str(test_params["spawn_rate"]),
                "--run-time", test_params["run_time"],
                "--headless",
                "--html", str(self.results_dir / f"load_test_{scenario}_{env_name}_{int(time.time())}.html")
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            # Parse results
            results = self._parse_locust_output(result.stdout)
            results["test_type"] = "load"
            results["scenario"] = scenario
            results["environment"] = env_name
            results["success"] = result.returncode == 0

            # Validate performance
            results["performance_validation"] = self._validate_performance(results)

            # Save results
            self._save_results(results, f"load_test_{scenario}_{env_name}")

            return results

        except Exception as e:
            return {"success": False, "error": str(e)}

        finally:
            # Cleanup
            self.env_manager.cleanup_environment(env_name)

    def _get_scenario_params(self, scenario: str, config: PerformanceEnvironmentConfig) -> Dict[str, Any]:
        """Get test parameters for scenario"""
        scenarios = {
            "smoke": {"users": 10, "spawn_rate": 2, "run_time": "60s"},
            "normal": {"users": min(100, config.max_concurrent_users), "spawn_rate": 10, "run_time": "10m"},
            "peak": {"users": min(500, config.max_concurrent_users), "spawn_rate": 50, "run_time": "5m"},
            "stress": {"users": min(1000, config.max_concurrent_users), "spawn_rate": 100, "run_time": "3m"},
            "endurance": {"users": min(200, config.max_concurrent_users), "spawn_rate": 20, "run_time": "30m"}
        }

        return scenarios.get(scenario, scenarios["normal"])

    def _parse_locust_output(self, output: str) -> Dict[str, Any]:
        """Parse Locust output to extract metrics"""
        # This is a simplified parser - in production, you'd want more robust parsing
        lines = output.split('\n')

        results = {
            "total_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0,
            "max_response_time": 0,
            "requests_per_second": 0,
            "test_duration": 0
        }

        for line in lines:
            if "Total requests" in line:
                try:
                    results["total_requests"] = int(line.split()[2])
                except:
                    pass
            elif "Failed requests" in line:
                try:
                    results["failed_requests"] = int(line.split()[2])
                except:
                    pass
            elif "Average response time" in line:
                try:
                    results["avg_response_time"] = float(line.split()[3])
                except:
                    pass
            elif "Max response time" in line:
                try:
                    results["max_response_time"] = float(line.split()[3])
                except:
                    pass
            elif "Requests per second" in line:
                try:
                    results["requests_per_second"] = float(line.split()[3])
                except:
                    pass

        return results

    def _validate_performance(self, results: Dict[str, Any]) -> Dict[str, bool]:
        """Validate performance against thresholds"""
        thresholds = {
            "max_response_time_ms": 2000,
            "max_error_rate_percent": 5,
            "min_throughput_rps": 10
        }

        validation = {}

        # Check response time
        avg_response_time_ms = results.get("avg_response_time", 0) * 1000
        validation["response_time"] = avg_response_time_ms <= thresholds["max_response_time_ms"]

        # Check error rate
        total_requests = results.get("total_requests", 0)
        failed_requests = results.get("failed_requests", 0)
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        validation["error_rate"] = error_rate <= thresholds["max_error_rate_percent"]

        # Check throughput
        throughput = results.get("requests_per_second", 0)
        validation["throughput"] = throughput >= thresholds["min_throughput_rps"]

        validation["overall"] = all(validation.values())

        return validation

    def _save_results(self, results: Dict[str, Any], test_name: str):
        """Save test results to file"""
        timestamp = int(time.time())
        filename = f"{test_name}_{timestamp}.json"
        filepath = self.results_dir / filename

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to: {filepath}")


def main():
    """Main function for running performance tests"""
    import argparse

    parser = argparse.ArgumentParser(description="PAKE System Performance Testing")
    parser.add_argument("--environment", "-e", default="local",
                       choices=["local", "staging", "production"],
                       help="Target environment")
    parser.add_argument("--scenario", "-s", default="smoke",
                       choices=["smoke", "normal", "peak", "stress", "endurance"],
                       help="Test scenario")
    parser.add_argument("--test-type", "-t", default="smoke",
                       choices=["smoke", "load"],
                       help="Type of test to run")

    args = parser.parse_args()

    # Initialize managers
    env_manager = PerformanceEnvironmentManager()
    test_runner = PerformanceTestRunner(env_manager)

    # Run test
    if args.test_type == "smoke":
        results = test_runner.run_smoke_test(args.environment)
    else:
        results = test_runner.run_load_test(args.environment, args.scenario)

    # Print results
    print("\n" + "="*50)
    print("PERFORMANCE TEST RESULTS")
    print("="*50)
    print(json.dumps(results, indent=2))

    if results.get("success"):
        print("\n✅ Test completed successfully")
    else:
        print(f"\n❌ Test failed: {results.get('error', 'Unknown error')}")
        exit(1)


if __name__ == "__main__":
    main()
