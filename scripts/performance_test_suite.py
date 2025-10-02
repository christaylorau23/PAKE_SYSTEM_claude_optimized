#!/usr/bin/env python3
"""
PAKE System - Performance Test Suite
Performance testing for CI/CD pipeline validation
"""

import asyncio
import json
import sys
import argparse
import time
from typing import Dict, List, Any
import httpx
import statistics


class PerformanceTestSuite:
    """Performance test suite for PAKE System"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.results = {
            "timestamp": time.time(),
            "base_url": base_url,
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "performance_issues": 0
            }
        }
    
    async def run_test(self, test_name: str, test_func) -> Dict[str, Any]:
        """Run a single performance test"""
        print(f"⚡ Running performance test: {test_name}")
        
        try:
            result = await test_func()
            self.results["tests"].append({
                "name": test_name,
                "status": "passed" if result["passed"] else "failed",
                "details": result.get("details", ""),
                "metrics": result.get("metrics", {}),
                "performance_issue": result.get("performance_issue", False)
            })
            
            if result["passed"]:
                self.results["summary"]["passed"] += 1
                print(f"✅ {test_name}: PASSED")
            else:
                self.results["summary"]["failed"] += 1
                if result.get("performance_issue", False):
                    self.results["summary"]["performance_issues"] += 1
                print(f"❌ {test_name}: FAILED - {result.get('details', '')}")
            
        except Exception as e:
            self.results["tests"].append({
                "name": test_name,
                "status": "error",
                "details": str(e),
                "performance_issue": True
            })
            self.results["summary"]["failed"] += 1
            self.results["summary"]["performance_issues"] += 1
            print(f"💥 {test_name}: ERROR - {str(e)}")
        
        self.results["summary"]["total"] += 1
        return {"status": "completed"}
    
    async def test_response_time(self) -> Dict[str, Any]:
        """Test response times for critical endpoints"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            endpoints = [
                "/health",
                "/auth/generate-password",
                "/api/v1/data",
                "/api/v1/search"
            ]
            
            response_times = []
            failed_requests = 0
            
            for endpoint in endpoints:
                try:
                    start_time = time.time()
                    response = await client.get(f"{self.base_url}{endpoint}")
                    end_time = time.time()
                    
                    response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                    response_times.append(response_time)
                    
                    if response.status_code >= 400:
                        failed_requests += 1
                        
                except Exception as e:
                    failed_requests += 1
                    print(f"Request to {endpoint} failed: {e}")
            
            avg_response_time = statistics.mean(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            
            # Performance thresholds (in milliseconds)
            avg_threshold = 1000  # 1 second
            max_threshold = 5000  # 5 seconds
            
            passed = (avg_response_time <= avg_threshold and 
                     max_response_time <= max_threshold and 
                     failed_requests == 0)
            
            return {
                "passed": passed,
                "performance_issue": not passed,
                "details": f"Avg: {avg_response_time:.2f}ms, Max: {max_response_time:.2f}ms, Failed: {failed_requests}",
                "metrics": {
                    "avg_response_time_ms": avg_response_time,
                    "max_response_time_ms": max_response_time,
                    "failed_requests": failed_requests,
                    "total_requests": len(endpoints)
                }
            }
    
    async def test_concurrent_requests(self) -> Dict[str, Any]:
        """Test system performance under concurrent load"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            concurrent_requests = 50
            endpoint = "/api/v1/data"
            
            async def make_request():
                try:
                    start_time = time.time()
                    response = await client.get(f"{self.base_url}{endpoint}")
                    end_time = time.time()
                    return {
                        "response_time": (end_time - start_time) * 1000,
                        "status_code": response.status_code,
                        "success": response.status_code < 400
                    }
                except Exception as e:
                    return {
                        "response_time": 0,
                        "status_code": 0,
                        "success": False,
                        "error": str(e)
                    }
            
            # Execute concurrent requests
            start_time = time.time()
            tasks = [make_request() for _ in range(concurrent_requests)]
            results = await asyncio.gather(*tasks)
            total_time = (time.time() - start_time) * 1000
            
            # Analyze results
            successful_requests = sum(1 for r in results if r["success"])
            response_times = [r["response_time"] for r in results if r["success"]]
            
            avg_response_time = statistics.mean(response_times) if response_times else 0
            throughput = successful_requests / (total_time / 1000) if total_time > 0 else 0
            
            # Performance thresholds
            success_rate_threshold = 0.95  # 95% success rate
            avg_response_time_threshold = 2000  # 2 seconds
            throughput_threshold = 10  # 10 requests per second
            
            success_rate = successful_requests / concurrent_requests
            passed = (success_rate >= success_rate_threshold and 
                     avg_response_time <= avg_response_time_threshold and
                     throughput >= throughput_threshold)
            
            return {
                "passed": passed,
                "performance_issue": not passed,
                "details": f"Success: {success_rate:.2%}, Avg: {avg_response_time:.2f}ms, Throughput: {throughput:.2f} req/s",
                "metrics": {
                    "concurrent_requests": concurrent_requests,
                    "successful_requests": successful_requests,
                    "success_rate": success_rate,
                    "avg_response_time_ms": avg_response_time,
                    "throughput_req_per_sec": throughput,
                    "total_time_ms": total_time
                }
            }
    
    async def test_memory_usage(self) -> Dict[str, Any]:
        """Test memory usage patterns"""
        # This is a simplified test - in production you'd use more sophisticated monitoring
        import psutil
        
        try:
            # Get initial memory usage
            initial_memory = psutil.virtual_memory().percent
            
            # Make some requests to potentially increase memory usage
            async with httpx.AsyncClient() as client:
                for _ in range(100):
                    try:
                        await client.get(f"{self.base_url}/api/v1/data")
                    except:
                        pass
            
            # Get final memory usage
            final_memory = psutil.virtual_memory().percent
            memory_increase = final_memory - initial_memory
            
            # Memory thresholds
            max_memory_increase = 10  # 10% increase
            max_total_memory = 80  # 80% total memory usage
            
            passed = (memory_increase <= max_memory_increase and 
                     final_memory <= max_total_memory)
            
            return {
                "passed": passed,
                "performance_issue": not passed,
                "details": f"Memory increase: {memory_increase:.2f}%, Total: {final_memory:.2f}%",
                "metrics": {
                    "initial_memory_percent": initial_memory,
                    "final_memory_percent": final_memory,
                    "memory_increase_percent": memory_increase
                }
            }
        except ImportError:
            return {
                "passed": True,
                "performance_issue": False,
                "details": "psutil not available, skipping memory test",
                "metrics": {}
            }
    
    async def test_database_performance(self) -> Dict[str, Any]:
        """Test database query performance"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test database-heavy endpoints
            db_endpoints = [
                "/api/v1/users",
                "/api/v1/search?q=test",
                "/api/v1/analytics"
            ]
            
            db_response_times = []
            failed_requests = 0
            
            for endpoint in db_endpoints:
                try:
                    start_time = time.time()
                    response = await client.get(f"{self.base_url}{endpoint}")
                    end_time = time.time()
                    
                    response_time = (end_time - start_time) * 1000
                    db_response_times.append(response_time)
                    
                    if response.status_code >= 400:
                        failed_requests += 1
                        
                except Exception as e:
                    failed_requests += 1
                    print(f"Database request to {endpoint} failed: {e}")
            
            avg_db_response_time = statistics.mean(db_response_times) if db_response_times else 0
            max_db_response_time = max(db_response_times) if db_response_times else 0
            
            # Database performance thresholds
            avg_db_threshold = 500  # 500ms
            max_db_threshold = 2000  # 2 seconds
            
            passed = (avg_db_response_time <= avg_db_threshold and 
                     max_db_response_time <= max_db_threshold and 
                     failed_requests == 0)
            
            return {
                "passed": passed,
                "performance_issue": not passed,
                "details": f"DB Avg: {avg_db_response_time:.2f}ms, Max: {max_db_response_time:.2f}ms, Failed: {failed_requests}",
                "metrics": {
                    "avg_db_response_time_ms": avg_db_response_time,
                    "max_db_response_time_ms": max_db_response_time,
                    "failed_db_requests": failed_requests
                }
            }
    
    async def run_all_tests(self):
        """Run all performance tests"""
        print("⚡ Starting PAKE System Performance Test Suite")
        print(f"Target URL: {self.base_url}")
        print("=" * 50)
        
        tests = [
            ("Response Time", self.test_response_time),
            ("Concurrent Requests", self.test_concurrent_requests),
            ("Memory Usage", self.test_memory_usage),
            ("Database Performance", self.test_database_performance),
        ]
        
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
        
        # Generate summary
        print("\n" + "=" * 50)
        print("⚡ Performance Test Suite Summary")
        print(f"Total Tests: {self.results['summary']['total']}")
        print(f"Passed: {self.results['summary']['passed']}")
        print(f"Failed: {self.results['summary']['failed']}")
        print(f"Performance Issues: {self.results['summary']['performance_issues']}")
        
        if self.results['summary']['performance_issues'] > 0:
            print("⚠️ Performance issues detected!")
            return False
        else:
            print("✅ All performance tests passed!")
            return True
    
    def save_report(self, filename: str = "performance_test_report.json"):
        """Save test results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"📄 Performance test report saved to {filename}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Performance Test Suite")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the application to test"
    )
    parser.add_argument(
        "--output",
        default="performance_test_report.json",
        help="Output file for test results"
    )
    
    args = parser.parse_args()
    
    test_suite = PerformanceTestSuite(args.base_url)
    success = await test_suite.run_all_tests()
    test_suite.save_report(args.output)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
