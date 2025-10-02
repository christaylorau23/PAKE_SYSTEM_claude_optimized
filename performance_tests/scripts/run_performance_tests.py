"""
Performance Testing Scripts
===========================

This directory contains scripts for running performance tests
against the PAKE System in different environments.

Usage:
    # Run smoke test locally
    python performance_tests/scripts/run_smoke_test.py
    
    # Run load test on staging
    python performance_tests/scripts/run_load_test.py --environment staging --scenario normal
    
    # Run stress test
    python performance_tests/scripts/run_load_test.py --scenario stress
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from environment_manager import PerformanceEnvironmentManager, PerformanceTestRunner
import argparse
import json
import time


def run_smoke_test():
    """Run smoke test for CI/CD pipeline"""
    print("🚀 Starting PAKE System Smoke Test")
    print("=" * 50)
    
    # Initialize managers
    env_manager = PerformanceEnvironmentManager()
    test_runner = PerformanceTestRunner(env_manager)
    
    # Run smoke test
    results = test_runner.run_smoke_test("local")
    
    # Print results
    print("\n📊 Smoke Test Results:")
    print("-" * 30)
    print(f"Success: {'✅' if results.get('success') else '❌'}")
    print(f"Total Requests: {results.get('total_requests', 0)}")
    print(f"Failed Requests: {results.get('failed_requests', 0)}")
    print(f"Avg Response Time: {results.get('avg_response_time', 0):.2f}s")
    print(f"Requests/Second: {results.get('requests_per_second', 0):.2f}")
    
    if not results.get('success'):
        print(f"Error: {results.get('error', 'Unknown error')}")
        return False
    
    return True


def run_load_test(environment: str = "local", scenario: str = "normal"):
    """Run comprehensive load test"""
    print(f"🚀 Starting PAKE System Load Test - {scenario.upper()}")
    print(f"Environment: {environment}")
    print("=" * 50)
    
    # Initialize managers
    env_manager = PerformanceEnvironmentManager()
    test_runner = PerformanceTestRunner(env_manager)
    
    # Run load test
    results = test_runner.run_load_test(environment, scenario)
    
    # Print results
    print("\n📊 Load Test Results:")
    print("-" * 30)
    print(f"Success: {'✅' if results.get('success') else '❌'}")
    print(f"Test Type: {results.get('test_type', 'unknown')}")
    print(f"Scenario: {results.get('scenario', 'unknown')}")
    print(f"Environment: {results.get('environment', 'unknown')}")
    print(f"Total Requests: {results.get('total_requests', 0)}")
    print(f"Failed Requests: {results.get('failed_requests', 0)}")
    print(f"Avg Response Time: {results.get('avg_response_time', 0):.2f}s")
    print(f"Max Response Time: {results.get('max_response_time', 0):.2f}s")
    print(f"Requests/Second: {results.get('requests_per_second', 0):.2f}")
    
    # Performance validation
    validation = results.get('performance_validation', {})
    if validation:
        print("\n🎯 Performance Validation:")
        print("-" * 30)
        print(f"Response Time: {'✅' if validation.get('response_time') else '❌'}")
        print(f"Error Rate: {'✅' if validation.get('error_rate') else '❌'}")
        print(f"Throughput: {'✅' if validation.get('throughput') else '❌'}")
        print(f"Overall: {'✅' if validation.get('overall') else '❌'}")
    
    if not results.get('success'):
        print(f"Error: {results.get('error', 'Unknown error')}")
        return False
    
    return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="PAKE System Performance Testing Scripts")
    parser.add_argument("--environment", "-e", default="local",
                       choices=["local", "staging", "production"],
                       help="Target environment")
    parser.add_argument("--scenario", "-s", default="normal",
                       choices=["smoke", "normal", "peak", "stress", "endurance"],
                       help="Test scenario")
    parser.add_argument("--test-type", "-t", default="smoke",
                       choices=["smoke", "load"],
                       help="Type of test to run")
    
    args = parser.parse_args()
    
    try:
        if args.test_type == "smoke":
            success = run_smoke_test()
        else:
            success = run_load_test(args.environment, args.scenario)
        
        if success:
            print("\n🎉 Performance test completed successfully!")
            return 0
        else:
            print("\n💥 Performance test failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
