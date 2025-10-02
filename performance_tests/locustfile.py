"""
PAKE System Performance Testing with Locust
==========================================

This file defines realistic user scenarios for load testing the PAKE System.
It simulates authentic user journeys across different personas and usage patterns.

Usage:
    # Run locally with web UI
    locust -f locustfile.py --host=http://localhost:8000
    
    # Run headless with specific parameters
    locust -f locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=5m --headless
    
    # Run against staging environment
    locust -f locustfile.py --host=https://staging.pake-system.com --users=50 --spawn-rate=5 --run-time=10m --headless

Personas:
- WebAppUser: Typical web application user browsing dashboards
- ApiUser: API-focused user making programmatic requests
- ResearcherUser: Heavy research user performing complex queries
- AdminUser: Administrative user managing system
"""

import json
import random
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

from locust import HttpUser, TaskSet, task, between
from locust.exception import StopUser


class BaseUserBehavior:
    """Base behavior shared across all user types"""
    
    def __init__(self, parent):
        self.parent = parent
        self.client = parent.client
        self.auth_token: Optional[str] = None
        self.user_id: Optional[str] = None
        
    def login(self) -> bool:
        """Authenticate user and store token"""
        try:
            # Test credentials for different user types
            # PAKE System uses /auth/token endpoint with OAuth2 flow
            credentials = {
                "username": "admin",
                "password": "secret"
            }

            response = self.client.post(
                "/auth/token",
                data=credentials,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                token_data = response.json()
                self.auth_token = token_data.get("access_token")
                return True
            else:
                print(f"Login failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        if not self.auth_token:
            return {}
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    def make_authenticated_request(self, method: str, url: str, **kwargs) -> 'Response':
        """Make an authenticated request"""
        headers = kwargs.get('headers', {})
        headers.update(self.get_auth_headers())
        kwargs['headers'] = headers
        return getattr(self.client, method.lower())(url, **kwargs)


class WebAppUserBehavior(BaseUserBehavior):
    """Behavior for typical web application users"""

    @task(10)
    def browse_dashboard(self):
        """Browse main dashboard - most common action"""
        self.client.get("/")

    @task(8)
    def get_user_info(self):
        """Get current user information (requires auth)"""
        if not self.auth_token:
            if not self.login():
                return

        self.make_authenticated_request("GET", "/auth/me")

    @task(6)
    def view_protected_content(self):
        """View protected content (requires auth)"""
        if not self.auth_token:
            if not self.login():
                return

        self.make_authenticated_request("GET", "/protected")

    @task(4)
    def view_admin_panel(self):
        """View admin panel (admin users only)"""
        if not self.auth_token:
            if not self.login():
                return

        self.make_authenticated_request("GET", "/admin")

    @task(3)
    def generate_password(self):
        """Generate secure password"""
        self.client.get("/auth/generate-password?length=16")

    @task(2)
    def view_docs(self):
        """View API documentation"""
        self.client.get("/docs")


class ApiUserBehavior(BaseUserBehavior):
    """Behavior for API-focused users"""

    @task(15)
    def api_root(self):
        """Check API root"""
        self.client.get("/")

    @task(12)
    def get_user_profile(self):
        """Get user profile via API"""
        if not self.auth_token:
            if not self.login():
                return

        self.make_authenticated_request("GET", "/auth/me")

    @task(8)
    def protected_api_call(self):
        """Make protected API calls"""
        if not self.auth_token:
            if not self.login():
                return

        self.make_authenticated_request("GET", "/protected")

    @task(5)
    def batch_requests(self):
        """Make multiple requests in sequence"""
        if not self.auth_token:
            if not self.login():
                return

        # Simulate batch processing
        for _ in range(3):
            self.make_authenticated_request("GET", "/auth/me")
            time.sleep(0.1)  # Small delay between requests

    @task(4)
    def password_operations(self):
        """Test password-related operations"""
        # Generate secure password
        self.client.get("/auth/generate-password?length=20")

        # Validate password strength
        self.client.post(
            "/auth/validate-password",
            json={"password": "TestPassword123!@#"}
        )

    @task(3)
    def error_scenarios(self):
        """Test error handling"""
        # Test 404
        self.client.get("/nonexistent-endpoint")

        # Test unauthorized access
        self.client.get("/protected")


class ResearcherUserBehavior(BaseUserBehavior):
    """Behavior for heavy research users - PAKE System focused on auth/admin operations"""

    def __init__(self, parent):
        super().__init__(parent)
        self.test_operations = [
            "user_profile",
            "password_generation",
            "password_validation",
            "protected_access",
            "admin_access"
        ]

    @task(20)
    def authenticated_operations(self):
        """Perform authenticated operations"""
        if not self.auth_token:
            if not self.login():
                return

        # Mix of different authenticated operations
        operation = random.choice(self.test_operations)

        if operation == "user_profile":
            self.make_authenticated_request("GET", "/auth/me")
        elif operation == "protected_access":
            self.make_authenticated_request("GET", "/protected")
        elif operation == "admin_access":
            self.make_authenticated_request("GET", "/admin")
        elif operation == "password_generation":
            self.client.get("/auth/generate-password?length=16")
        elif operation == "password_validation":
            self.client.post(
                "/auth/validate-password",
                json={"password": "SecureTestPassword123!@#"}
            )

    @task(8)
    def quick_operations(self):
        """Perform quick authenticated checks"""
        if not self.auth_token:
            if not self.login():
                return

        # Quick profile check
        self.make_authenticated_request("GET", "/auth/me")

    @task(5)
    def batch_profile_checks(self):
        """Batch profile information requests"""
        if not self.auth_token:
            if not self.login():
                return

        # Simulate checking profile multiple times
        for _ in range(5):
            self.make_authenticated_request("GET", "/auth/me")
            time.sleep(0.05)

    @task(3)
    def password_operations(self):
        """Test password-related operations"""
        # Generate multiple passwords
        for length in [12, 16, 20, 24]:
            self.client.get(f"/auth/generate-password?length={length}")
            time.sleep(0.1)


class AdminUserBehavior(BaseUserBehavior):
    """Behavior for administrative users"""

    @task(8)
    def system_monitoring(self):
        """Monitor system health and admin panel"""
        if not self.auth_token:
            if not self.login():
                return

        # Check admin panel
        self.make_authenticated_request("GET", "/admin")

        # Check own profile
        self.make_authenticated_request("GET", "/auth/me")

    @task(6)
    def user_operations(self):
        """Perform user-related administrative operations"""
        if not self.auth_token:
            if not self.login():
                return

        # Get user profile
        self.make_authenticated_request("GET", "/auth/me")

        # Access protected resources
        self.make_authenticated_request("GET", "/protected")

    @task(4)
    def password_management(self):
        """Manage password generation and validation"""
        # Generate passwords for users
        for _ in range(3):
            self.client.get("/auth/generate-password?length=20")
            time.sleep(0.1)

        # Validate password strength
        test_passwords = [
            "weak",
            "StrongerPass123",
            "VerySecure!Pass123@"
        ]

        for password in test_passwords:
            self.client.post(
                "/auth/validate-password",
                json={"password": password}
            )
            time.sleep(0.1)

    @task(2)
    def security_checks(self):
        """Perform security-related checks"""
        if not self.auth_token:
            if not self.login():
                return

        # Check admin access
        self.make_authenticated_request("GET", "/admin")

        # Check protected access
        self.make_authenticated_request("GET", "/protected")

        # Generate secure passwords
        self.client.get("/auth/generate-password?length=32")


class WebAppUser(HttpUser):
    """Typical web application user"""
    weight = 40  # 40% of users
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when user starts"""
        self.behavior = WebAppUserBehavior(self)
    
    @task
    def user_tasks(self):
        """Execute user tasks"""
        self.behavior.browse_dashboard()
        self.behavior.check_health()
        self.behavior.view_protected_content()
        self.behavior.view_admin_panel()
        self.behavior.view_docs()


class ApiUser(HttpUser):
    """API-focused user"""
    weight = 30  # 30% of users
    wait_time = between(0.5, 2)  # Faster requests
    
    def on_start(self):
        """Called when user starts"""
        self.behavior = ApiUserBehavior(self)
    
    @task
    def api_tasks(self):
        """Execute API tasks"""
        self.behavior.health_check()
        self.behavior.api_root()
        self.behavior.protected_api_call()
        self.behavior.batch_requests()
        self.behavior.error_scenarios()


class ResearcherUser(HttpUser):
    """Heavy research user"""
    weight = 20  # 20% of users
    wait_time = between(2, 5)  # Longer waits for complex operations
    
    def on_start(self):
        """Called when user starts"""
        self.behavior = ResearcherUserBehavior(self)
    
    @task
    def research_tasks(self):
        """Execute research tasks"""
        self.behavior.complex_search()
        self.behavior.quick_search()
        self.behavior.analytics_request()
        self.behavior.content_analysis()


class AdminUser(HttpUser):
    """Administrative user"""
    weight = 10  # 10% of users
    wait_time = between(1, 4)  # Moderate waits
    
    def on_start(self):
        """Called when user starts"""
        self.behavior = AdminUserBehavior(self)
    
    @task
    def admin_tasks(self):
        """Execute admin tasks"""
        self.behavior.system_monitoring()
        self.behavior.user_management()
        self.behavior.system_configuration()
        self.behavior.security_audit()


# Performance test scenarios
class PerformanceTestScenarios:
    """Predefined test scenarios for different load patterns"""
    
    @staticmethod
    def smoke_test():
        """Light load test for CI/CD pipeline"""
        return {
            "users": 10,
            "spawn_rate": 2,
            "run_time": "60s",
            "description": "Smoke test for CI/CD pipeline"
        }
    
    @staticmethod
    def normal_load():
        """Normal production load"""
        return {
            "users": 100,
            "spawn_rate": 10,
            "run_time": "10m",
            "description": "Normal production load"
        }
    
    @staticmethod
    def peak_load():
        """Peak production load"""
        return {
            "users": 500,
            "spawn_rate": 50,
            "run_time": "5m",
            "description": "Peak production load"
        }
    
    @staticmethod
    def stress_test():
        """Stress test to find breaking point"""
        return {
            "users": 1000,
            "spawn_rate": 100,
            "run_time": "3m",
            "description": "Stress test to find breaking point"
        }
    
    @staticmethod
    def endurance_test():
        """Long-running test for memory leaks"""
        return {
            "users": 200,
            "spawn_rate": 20,
            "run_time": "30m",
            "description": "Endurance test for memory leaks"
        }


# Custom metrics collection
class CustomMetrics:
    """Custom metrics for detailed performance analysis"""
    
    def __init__(self):
        self.metrics = {
            "response_times": [],
            "error_rates": {},
            "throughput": 0,
            "concurrent_users": 0
        }
    
    def record_response_time(self, response_time: float):
        """Record response time"""
        self.metrics["response_times"].append(response_time)
    
    def record_error(self, status_code: int):
        """Record error"""
        if status_code not in self.metrics["error_rates"]:
            self.metrics["error_rates"][status_code] = 0
        self.metrics["error_rates"][status_code] += 1
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        if not self.metrics["response_times"]:
            return self.metrics
        
        response_times = self.metrics["response_times"]
        return {
            "avg_response_time": sum(response_times) / len(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)],
            "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)],
            "error_rates": self.metrics["error_rates"],
            "total_requests": len(response_times)
        }


# Global metrics instance
custom_metrics = CustomMetrics()


def on_request_success(request_type, name, response_time, response_length):
    """Called on successful request"""
    custom_metrics.record_response_time(response_time)


def on_request_failure(request_type, name, response_time, response_length, exception):
    """Called on failed request"""
    custom_metrics.record_error(500)  # Assume 500 for exceptions


# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    "max_response_time_ms": 2000,  # 2 seconds
    "max_error_rate_percent": 5,   # 5% error rate
    "min_throughput_rps": 10,       # 10 requests per second
    "max_p95_response_time_ms": 1000,  # 1 second for 95th percentile
}


def validate_performance(results: Dict) -> Dict[str, bool]:
    """Validate performance against thresholds"""
    validation = {}
    
    # Check response time
    avg_response_time = results.get("avg_response_time", 0) * 1000  # Convert to ms
    validation["response_time"] = avg_response_time <= PERFORMANCE_THRESHOLDS["max_response_time_ms"]
    
    # Check error rate
    total_requests = results.get("total_requests", 0)
    total_errors = sum(results.get("error_rates", {}).values())
    error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
    validation["error_rate"] = error_rate <= PERFORMANCE_THRESHOLDS["max_error_rate_percent"]
    
    # Check throughput (requests per second)
    throughput = total_requests / (results.get("test_duration", 1) / 60)  # Convert to RPS
    validation["throughput"] = throughput >= PERFORMANCE_THRESHOLDS["min_throughput_rps"]
    
    return validation


if __name__ == "__main__":
    # This allows running the file directly for testing
    import subprocess
    import sys
    
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
        if scenario in ["smoke", "normal", "peak", "stress", "endurance"]:
            config = getattr(PerformanceTestScenarios, f"{scenario}_test")()
            cmd = [
                "locust",
                "-f", __file__,
                "--host=http://localhost:8000",
                "--users", str(config["users"]),
                "--spawn-rate", str(config["spawn_rate"]),
                "--run-time", config["run_time"],
                "--headless"
            ]
            subprocess.run(cmd)
        else:
            print(f"Unknown scenario: {scenario}")
            print("Available scenarios: smoke, normal, peak, stress, endurance")
    else:
        print("PAKE System Performance Testing")
        print("Usage: python locustfile.py [scenario]")
        print("Scenarios: smoke, normal, peak, stress, endurance")
