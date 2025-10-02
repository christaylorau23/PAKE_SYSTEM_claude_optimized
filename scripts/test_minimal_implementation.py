"""
Simple Test Runner for Minimal Implementation
Verifies our TDD Green Phase implementation without external dependencies

This script tests the minimal services we created to make sure they satisfy
the basic contract requirements before moving to the Refactor phase.
"""

import json
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SimpleTestRunner:
    """Simple test runner without external dependencies"""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.services_started = []

    def log(self, message: str, level: str = "INFO"):
        """Simple logging"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def assert_equal(self, actual, expected, message: str):
        """Simple assertion"""
        if actual == expected:
            self.tests_passed += 1
            self.log(f"✓ {message}")
        else:
            self.tests_failed += 1
            self.log(f"✗ {message}: expected {expected}, got {actual}", "ERROR")

    def assert_in(self, item, container, message: str):
        """Assert item is in container"""
        if item in container:
            self.tests_passed += 1
            self.log(f"✓ {message}")
        else:
            self.tests_failed += 1
            self.log(f"✗ {message}: {item} not found", "ERROR")

    def assert_status_code(self, url: str, expected_status: int, message: str):
        """Check HTTP status code"""
        try:
            response = urlopen(url, timeout=5)
            actual_status = response.getcode()
            self.assert_equal(actual_status, expected_status, message)
            return response
        except HTTPError as e:
            actual_status = e.code
            self.assert_equal(actual_status, expected_status, message)
            return None
        except URLError as e:
            self.tests_failed += 1
            self.log(f"✗ {message}: Connection failed - {e}", "ERROR")
            return None

    def start_service(self, script_path: str, port: int, service_name: str):
        """Start a service in background"""
        try:
            self.log(f"Starting {service_name} on port {port}...")
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Wait a moment for service to start
            time.sleep(2)

            # Check if service is responding
            try:
                urlopen(f"http://localhost:{port}/docs", timeout=5)
                self.log(f"✓ {service_name} started successfully")
                self.services_started.append((process, service_name))
                return process
            except:
                self.log(f"✗ {service_name} failed to start", "ERROR")
                process.terminate()
                return None

        except Exception as e:
            self.log(f"✗ Failed to start {service_name}: {e}", "ERROR")
            return None

    def test_api_gateway_health(self):
        """Test API Gateway health endpoint (Contract Test T007)"""
        self.log("Testing API Gateway health endpoint...")

        # Test health endpoint exists
        response = self.assert_status_code(
            "http://localhost:8080/v1/health",
            200,
            "API Gateway health endpoint responds with 200",
        )

        if response:
            try:
                data = json.loads(response.read().decode())

                # Test required fields
                self.assert_in("status", data, "Health response contains status field")
                self.assert_in(
                    "timestamp", data, "Health response contains timestamp field"
                )
                self.assert_in(
                    "services", data, "Health response contains services field"
                )

                # Test status values
                valid_statuses = ["healthy", "degraded", "unhealthy"]
                self.assert_in(
                    data["status"], valid_statuses, "Health status is valid enum value"
                )

                # Test services structure
                if "services" in data:
                    expected_services = [
                        "service-registry",
                        "research-orchestrator",
                        "cache-service",
                        "performance-monitor",
                    ]
                    for service in expected_services:
                        self.assert_in(
                            service,
                            data["services"],
                            f"Health includes {service} status",
                        )

            except json.JSONDecodeError:
                self.tests_failed += 1
                self.log("✗ Health response is not valid JSON", "ERROR")

    def test_api_gateway_routing(self):
        """Test API Gateway routing (Contract Test T008)"""
        self.log("Testing API Gateway routing...")

        # Test service discovery
        response = self.assert_status_code(
            "http://localhost:8080/v1/services",
            200,
            "Service discovery endpoint responds",
        )

        if response:
            try:
                services = json.loads(response.read().decode())
                if isinstance(services, list) and len(services) > 0:
                    self.tests_passed += 1
                    self.log("✓ Service discovery returns service list")

                    # Check for expected services
                    service_names = [s.get("name", "") for s in services]
                    for expected in ["research", "cache", "performance"]:
                        self.assert_in(
                            expected,
                            service_names,
                            f"Service discovery includes {expected}",
                        )
                else:
                    self.tests_failed += 1
                    self.log(
                        "✗ Service discovery returns empty or invalid data", "ERROR"
                    )

            except json.JSONDecodeError:
                self.tests_failed += 1
                self.log("✗ Service discovery response is not valid JSON", "ERROR")

        # Test cache service routing
        response = self.assert_status_code(
            "http://localhost:8080/v1/services/cache/stats",
            200,
            "Cache service routing works",
        )

        if response:
            try:
                data = json.loads(response.read().decode())
                self.assert_in(
                    "hit_rate", data, "Cache stats response contains hit_rate"
                )
            except json.JSONDecodeError:
                self.tests_failed += 1
                self.log("✗ Cache stats response is not valid JSON", "ERROR")

    def test_service_registry(self):
        """Test Service Registry (Integration Test T013)"""
        self.log("Testing Service Registry...")

        # Test service registration
        test_service = {
            "service_name": "test-service-simple",
            "service_version": "1.0.0",
            "service_type": "API",
            "environment": "DEVELOPMENT",
            "base_url": "http://localhost:8090",
            "health_check_url": "http://localhost:8090/health",
        }

        try:
            # Register service
            req = Request(
                "http://localhost:8000/api/v1/services/register",
                data=json.dumps(test_service).encode(),
                headers={"Content-Type": "application/json"},
            )

            response = urlopen(req, timeout=5)
            if response.getcode() == 201:
                self.tests_passed += 1
                self.log("✓ Service registration successful")

                reg_data = json.loads(response.read().decode())
                if "service_id" in reg_data:
                    self.tests_passed += 1
                    self.log("✓ Registration returns service_id")

                    service_id = reg_data["service_id"]

                    # Test service discovery
                    discovery_response = urlopen(
                        "http://localhost:8000/api/v1/services", timeout=5
                    )
                    if discovery_response.getcode() == 200:
                        services = json.loads(discovery_response.read().decode())
                        found_service = any(
                            s.get("service_id") == service_id for s in services
                        )

                        if found_service:
                            self.tests_passed += 1
                            self.log("✓ Registered service appears in discovery")
                        else:
                            self.tests_failed += 1
                            self.log(
                                "✗ Registered service not found in discovery", "ERROR"
                            )

                    # Cleanup
                    cleanup_req = Request(
                        f"http://localhost:8000/api/v1/services/{service_id}",
                        method="DELETE",
                    )
                    cleanup_req.get_method = lambda: "DELETE"
                    urlopen(cleanup_req, timeout=5)

                else:
                    self.tests_failed += 1
                    self.log("✗ Registration response missing service_id", "ERROR")
            else:
                self.tests_failed += 1
                self.log(
                    f"✗ Service registration failed with status {response.getcode()}",
                    "ERROR",
                )

        except Exception as e:
            self.tests_failed += 1
            self.log(f"✗ Service registry test failed: {e}", "ERROR")

    def test_monitoring_metrics(self):
        """Test Monitoring metrics (Contract Test T010)"""
        self.log("Testing Monitoring metrics...")

        # Test Prometheus metrics endpoint
        response = self.assert_status_code(
            "http://localhost:9090/api/v1/metrics",
            200,
            "Prometheus metrics endpoint responds",
        )

        if response:
            metrics_text = response.read().decode()

            # Check for required metrics
            required_metrics = [
                "pake_research_requests_total",
                "pake_request_duration_seconds",
                "pake_cache_hit_rate",
                "pake_database_connections_active",
                "pake_service_health_status",
            ]

            for metric in required_metrics:
                self.assert_in(metric, metrics_text, f"Metrics include {metric}")

            # Check format
            self.assert_in("# HELP", metrics_text, "Metrics include HELP comments")
            self.assert_in("# TYPE", metrics_text, "Metrics include TYPE comments")

        # Test custom metrics endpoint
        response = self.assert_status_code(
            "http://localhost:9090/api/v1/metrics/custom",
            200,
            "Custom metrics endpoint responds",
        )

        if response:
            try:
                data = json.loads(response.read().decode())
                self.assert_in("timestamp", data, "Custom metrics include timestamp")
                self.assert_in(
                    "service_metrics", data, "Custom metrics include service_metrics"
                )
            except json.JSONDecodeError:
                self.tests_failed += 1
                self.log("✗ Custom metrics response is not valid JSON", "ERROR")

    def cleanup_services(self):
        """Stop all started services"""
        self.log("Cleaning up services...")
        for process, name in self.services_started:
            try:
                process.terminate()
                process.wait(timeout=5)
                self.log(f"✓ Stopped {name}")
            except:
                try:
                    process.kill()
                    self.log(f"✓ Killed {name}")
                except:
                    self.log(f"✗ Failed to stop {name}", "ERROR")

    def run_all_tests(self):
        """Run all TDD validation tests"""
        self.log("=== TDD Green Phase Validation ===")
        self.log("Testing minimal implementation to verify contracts pass...")

        # Start services
        api_gateway = self.start_service(
            "src/services/orchestration/api_gateway.py", 8080, "API Gateway"
        )

        service_registry = self.start_service(
            "src/services/orchestration/service_registry.py", 8000, "Service Registry"
        )

        monitoring = self.start_service(
            "src/services/observability/monitoring_service.py",
            9090,
            "Monitoring Service",
        )

        # Wait for services to fully start
        time.sleep(3)

        try:
            # Run tests
            if api_gateway:
                self.test_api_gateway_health()
                self.test_api_gateway_routing()

            if service_registry:
                self.test_service_registry()

            if monitoring:
                self.test_monitoring_metrics()

        finally:
            self.cleanup_services()

        # Report results
        total_tests = self.tests_passed + self.tests_failed
        self.log("=== Test Results ===")
        self.log(f"Total Tests: {total_tests}")
        self.log(f"Passed: {self.tests_passed}")
        self.log(f"Failed: {self.tests_failed}")

        if self.tests_failed == 0:
            self.log("🟢 ALL TESTS PASSED - TDD Green Phase Complete!", "SUCCESS")
            return True
        else:
            self.log(f"🔴 {self.tests_failed} tests failed - needs fixes", "ERROR")
            return False


if __name__ == "__main__":
    runner = SimpleTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)
