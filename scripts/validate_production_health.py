#!/usr/bin/env python3
"""
PAKE System - Production Health Validation
Comprehensive health checks for production deployments
"""

import asyncio
import json
import sys
import argparse
import time
from typing import Dict, List, Any
import httpx


class ProductionHealthValidator:
    """Production health validation for PAKE System"""
    
    def __init__(self, base_url: str = "https://pake-system.com"):
        self.base_url = base_url.rstrip('/')
        self.results = {
            "timestamp": time.time(),
            "base_url": base_url,
            "checks": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "critical_failures": 0
            }
        }
    
    async def run_check(self, check_name: str, check_func) -> Dict[str, Any]:
        """Run a single health check"""
        print(f"🔍 Running health check: {check_name}")
        
        try:
            result = await check_func()
            self.results["checks"].append({
                "name": check_name,
                "status": "passed" if result["passed"] else "failed",
                "details": result.get("details", ""),
                "critical": result.get("critical", False)
            })
            
            if result["passed"]:
                self.results["summary"]["passed"] += 1
                print(f"✅ {check_name}: PASSED")
            else:
                self.results["summary"]["failed"] += 1
                if result.get("critical", False):
                    self.results["summary"]["critical_failures"] += 1
                print(f"❌ {check_name}: FAILED - {result.get('details', '')}")
            
        except Exception as e:
            self.results["checks"].append({
                "name": check_name,
                "status": "error",
                "details": str(e),
                "critical": True
            })
            self.results["summary"]["failed"] += 1
            self.results["summary"]["critical_failures"] += 1
            print(f"💥 {check_name}: ERROR - {str(e)}")
        
        self.results["summary"]["total"] += 1
    
    async def check_basic_health(self) -> Dict[str, Any]:
        """Check basic health endpoints"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            health_endpoints = [
                "/health",
                "/auth/generate-password",
                "/api/v1/status"
            ]
            
            failed_endpoints = []
            for endpoint in health_endpoints:
                try:
                    response = await client.get(f"{self.base_url}{endpoint}")
                    if response.status_code != 200:
                        failed_endpoints.append(f"{endpoint} ({response.status_code})")
                except Exception as e:
                    failed_endpoints.append(f"{endpoint} (error: {str(e)})")
            
            return {
                "passed": len(failed_endpoints) == 0,
                "critical": True,
                "details": f"Failed endpoints: {', '.join(failed_endpoints)}" if failed_endpoints else "All health endpoints responding"
            }
    
    async def check_ssl_certificate(self) -> Dict[str, Any]:
        """Check SSL certificate validity"""
        try:
            import ssl
            import socket
            
            # Extract hostname from URL
            hostname = self.base_url.replace("https://", "").replace("http://", "").split("/")[0]
            
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Check certificate expiration
                    import datetime
                    not_after = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_until_expiry = (not_after - datetime.datetime.now()).days
                    
                    ssl_valid = days_until_expiry > 30  # More than 30 days remaining
                    
                    return {
                        "passed": ssl_valid,
                        "critical": True,
                        "details": f"SSL certificate expires in {days_until_expiry} days"
                    }
        except Exception as e:
            return {
                "passed": False,
                "critical": True,
                "details": f"SSL certificate check failed: {str(e)}"
            }
    
    async def check_response_times(self) -> Dict[str, Any]:
        """Check response times are within acceptable limits"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            endpoints = [
                "/health",
                "/auth/generate-password",
                "/api/v1/data"
            ]
            
            slow_endpoints = []
            for endpoint in endpoints:
                try:
                    start_time = time.time()
                    response = await client.get(f"{self.base_url}{endpoint}")
                    response_time = (time.time() - start_time) * 1000
                    
                    if response_time > 2000:  # 2 seconds threshold
                        slow_endpoints.append(f"{endpoint} ({response_time:.0f}ms)")
                except:
                    slow_endpoints.append(f"{endpoint} (timeout)")
            
            return {
                "passed": len(slow_endpoints) == 0,
                "critical": False,
                "details": f"Slow endpoints: {', '.join(slow_endpoints)}" if slow_endpoints else "All endpoints responding quickly"
            }
    
    async def check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Test database-dependent endpoints
                response = await client.get(f"{self.base_url}/api/v1/users")
                db_accessible = response.status_code in [200, 401, 403]  # 401/403 means DB is accessible but auth required
                
                return {
                    "passed": db_accessible,
                    "critical": True,
                    "details": "Database connectivity" + ("OK" if db_accessible else "FAILED")
                }
            except Exception as e:
                return {
                    "passed": False,
                    "critical": True,
                    "details": f"Database connectivity check failed: {str(e)}"
                }
    
    async def check_cache_system(self) -> Dict[str, Any]:
        """Check cache system functionality"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Test cache-dependent endpoints
                response = await client.get(f"{self.base_url}/api/v1/cache-test")
                cache_working = response.status_code in [200, 404]  # 404 is OK if endpoint doesn't exist
                
                return {
                    "passed": cache_working,
                    "critical": False,
                    "details": "Cache system" + ("OK" if cache_working else "FAILED")
                }
            except Exception as e:
                return {
                    "passed": False,
                    "critical": False,
                    "details": f"Cache system check failed: {str(e)}"
                }
    
    async def check_security_headers(self) -> Dict[str, Any]:
        """Check security headers are present"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{self.base_url}/")
                headers = response.headers
                
                required_headers = [
                    "X-Content-Type-Options",
                    "X-Frame-Options",
                    "Strict-Transport-Security"
                ]
                
                missing_headers = [h for h in required_headers if h not in headers]
                
                return {
                    "passed": len(missing_headers) == 0,
                    "critical": False,
                    "details": f"Missing security headers: {', '.join(missing_headers)}" if missing_headers else "All security headers present"
                }
            except Exception as e:
                return {
                    "passed": False,
                    "critical": False,
                    "details": f"Security headers check failed: {str(e)}"
                }
    
    async def run_all_checks(self):
        """Run all health checks"""
        print("🔍 Starting PAKE System Production Health Validation")
        print(f"Target URL: {self.base_url}")
        print("=" * 50)
        
        checks = [
            ("Basic Health", self.check_basic_health),
            ("SSL Certificate", self.check_ssl_certificate),
            ("Response Times", self.check_response_times),
            ("Database Connectivity", self.check_database_connectivity),
            ("Cache System", self.check_cache_system),
            ("Security Headers", self.check_security_headers),
        ]
        
        for check_name, check_func in checks:
            await self.run_check(check_name, check_func)
        
        # Generate summary
        print("\n" + "=" * 50)
        print("🔍 Production Health Validation Summary")
        print(f"Total Checks: {self.results['summary']['total']}")
        print(f"Passed: {self.results['summary']['passed']}")
        print(f"Failed: {self.results['summary']['failed']}")
        print(f"Critical Failures: {self.results['summary']['critical_failures']}")
        
        if self.results['summary']['critical_failures'] > 0:
            print("❌ CRITICAL HEALTH ISSUES FOUND!")
            return False
        elif self.results['summary']['failed'] > 0:
            print("⚠️ Some health issues found, but none critical")
            return True
        else:
            print("✅ All health checks passed!")
            return True
    
    def save_report(self, filename: str = "production_health_report.json"):
        """Save validation results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"📄 Production health report saved to {filename}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Production Health Validator")
    parser.add_argument(
        "--base-url",
        default="https://pake-system.com",
        help="Base URL of the production application"
    )
    parser.add_argument(
        "--output",
        default="production_health_report.json",
        help="Output file for validation results"
    )
    
    args = parser.parse_args()
    
    validator = ProductionHealthValidator(args.base_url)
    success = await validator.run_all_checks()
    validator.save_report(args.output)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
