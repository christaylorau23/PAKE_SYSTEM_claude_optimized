#!/usr/bin/env python3
"""
PAKE System - Multi-Tenant Server Validation Script
Quick validation script to test multi-tenant server functionality.
"""

import asyncio
import sys
from datetime import datetime

import httpx


async def test_multitenant_server():
    """Test basic multi-tenant server functionality"""

    base_url = "http://localhost:8000"
    api_prefix = "/api/v1"

    print("🚀 Testing PAKE Multi-Tenant Server...")
    print("=" * 50)

    test_results = []

    # Test 1: Health endpoint
    print("🔍 Testing health endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")
            test_results.append(
                {
                    "test": "health_endpoint",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response": (
                        response.json()
                        if response.status_code == 200
                        else response.text
                    ),
                },
            )
            print(f"   Status: {response.status_code}")
    except Exception as e:
        test_results.append(
            {"test": "health_endpoint", "success": False, "error": str(e)},
        )
        print(f"   Error: {e}")

    # Test 2: System status
    print("🔍 Testing system status...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}{api_prefix}/system/status")
            test_results.append(
                {
                    "test": "system_status",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response": (
                        response.json()
                        if response.status_code == 200
                        else response.text
                    ),
                },
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   System: {data.get('system', 'Unknown')}")
                print(f"   Version: {data.get('version', 'Unknown')}")
    except Exception as e:
        test_results.append(
            {"test": "system_status", "success": False, "error": str(e)},
        )
        print(f"   Error: {e}")

    # Test 3: OpenAPI docs
    print("🔍 Testing OpenAPI documentation...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/docs")
            test_results.append(
                {
                    "test": "openapi_docs",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                },
            )
            print(f"   Status: {response.status_code}")
    except Exception as e:
        test_results.append({"test": "openapi_docs", "success": False, "error": str(e)})
        print(f"   Error: {e}")

    # Test 4: Metrics endpoint (if available)
    print("🔍 Testing metrics endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}{api_prefix}/system/metrics")
            test_results.append(
                {
                    "test": "metrics_endpoint",
                    # 404 is acceptable if metrics disabled
                    "success": response.status_code in [200, 404],
                    "status_code": response.status_code,
                },
            )
            print(f"   Status: {response.status_code}")
    except Exception as e:
        test_results.append(
            {
                "test": "metrics_endpoint",
                "success": True,  # Don't fail if metrics not available
                "error": str(e),
            },
        )
        print(f"   Warning: {e}")

    # Test 5: Authentication endpoints (expect 401/403 without auth)
    print("🔍 Testing authentication protection...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}{api_prefix}/tenants/")
            test_results.append(
                {
                    "test": "auth_protection",
                    "success": response.status_code
                    in [401, 403],  # Should be protected
                    "status_code": response.status_code,
                },
            )
            print(f"   Status: {response.status_code} (expected 401/403)")
    except Exception as e:
        test_results.append(
            {"test": "auth_protection", "success": False, "error": str(e)},
        )
        print(f"   Error: {e}")

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = sum(1 for test in test_results if test["success"])
    total = len(test_results)
    success_rate = (passed / total * 100) if total > 0 else 0

    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {success_rate:.1f}%")

    for test in test_results:
        status = "✅ PASS" if test["success"] else "❌ FAIL"
        print(f"{status} {test['test']}")
        if not test["success"] and "error" in test:
            print(f"    Error: {test['error']}")

    overall_status = "✅ SUCCESS" if passed == total else "❌ SOME FAILURES"
    print(f"\nOverall Status: {overall_status}")

    return passed == total


async def main():
    """Main execution"""
    print(f"PAKE Multi-Tenant Server Test - {datetime.now()}")
    print("Testing basic server functionality...\n")

    success = await test_multitenant_server()

    if success:
        print("\n🎉 All tests passed! Server is ready for multi-tenant operations.")
        return 0
    print("\n⚠️ Some tests failed. Please check server configuration.")
    return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        sys.exit(1)
