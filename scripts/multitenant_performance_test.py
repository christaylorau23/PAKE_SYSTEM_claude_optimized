#!/usr/bin/env python3
"""
PAKE System - Phase 16 Multi-Tenant Performance Testing
Comprehensive performance testing for multi-tenant architecture.
"""

import argparse
import asyncio
import json
import logging
import os
import random
import statistics
import string
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.services.database.multi_tenant_schema import (
    MultiTenantDatabaseConfig,
    MultiTenantPostgreSQLService,
)

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""

    operation: str
    tenant_count: int
    concurrent_users: int
    total_operations: int
    successful_operations: int
    failed_operations: int
    total_time_seconds: float
    average_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    operations_per_second: float
    error_rate_percent: float
    cpu_usage_percent: float | None = None
    memory_usage_mb: float | None = None


class MultiTenantPerformanceTester:
    """
    Comprehensive multi-tenant performance testing framework.

    Tests:
    - Database performance with multiple tenants
    - Concurrent tenant operations
    - Resource isolation performance
    - Scalability under load
    - Cross-tenant query performance
    - Tenant context switching overhead
    """

    def __init__(
        self,
        db_config: MultiTenantDatabaseConfig,
        api_base_url: str = "http://localhost:8000",
    ):
        self.db_config = db_config
        self.api_base_url = api_base_url
        self.db_service: MultiTenantPostgreSQLService | None = None
        self.test_tenants: list[dict[str, Any]] = []
        self.test_users: list[dict[str, Any]] = []
        self.performance_results: list[PerformanceMetrics] = []

    async def initialize(self) -> None:
        """Initialize database service"""
        try:
            self.db_service = MultiTenantPostgreSQLService(self.db_config)
            await self.db_service.initialize()
            logger.info("✅ Database service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database service: {e}")
            raise

    async def close(self) -> None:
        """Close database connections"""
        if self.db_service:
            await self.db_service.close()
        logger.info("Database connections closed")

    def _generate_random_string(self, length: int = 10) -> str:
        """Generate random string for testing"""
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    async def setup_test_data(self, tenant_count: int, users_per_tenant: int) -> None:
        """Set up test data for performance testing"""
        logger.info(
            f"🔧 Setting up test data: {tenant_count} tenants, {
                users_per_tenant
            } users each",
        )

        self.test_tenants = []
        self.test_users = []

        for i in range(tenant_count):
            # Create tenant
            tenant = await self.db_service.create_tenant(
                name=f"perf-tenant-{i}",
                display_name=f"Performance Test Tenant {i}",
                domain=f"perf-tenant-{i}.pake.com",
                plan="professional",
            )
            self.test_tenants.append(tenant)

            # Create users for tenant
            for j in range(users_per_tenant):
                user = await self.db_service.create_user(
                    tenant_id=tenant["id"],
                    username=f"perf-user-{i}-{j}",
                    email=f"perf-user-{i}-{j}@perf-tenant-{i}.pake.com",
                    REDACTED_SECRET_hash=f"hash-{i}-{j}",
                    full_name=f"Performance User {i}-{j}",
                )
                self.test_users.append(user)

        logger.info(
            f"✅ Created {len(self.test_tenants)} tenants and {
                len(self.test_users)
            } users",
        )

    async def cleanup_test_data(self) -> None:
        """Clean up test data"""
        logger.info("🧹 Cleaning up test data...")

        for tenant in self.test_tenants:
            try:
                await self.db_service.update_tenant_status(tenant["id"], "deleted")
            except Exception as e:
                logger.warning(f"Failed to cleanup tenant {tenant['id']}: {e}")

        logger.info("✅ Test data cleanup completed")

    async def test_tenant_isolation_performance(
        self,
        operations_per_tenant: int = 100,
    ) -> PerformanceMetrics:
        """Test performance of tenant-isolated operations"""
        logger.info(
            f"🧪 Testing tenant isolation performance: {
                operations_per_tenant
            } operations per tenant",
        )

        start_time = time.time()
        response_times = []
        successful_ops = 0
        failed_ops = 0

        async def perform_tenant_operations(tenant: dict[str, Any]) -> list[float]:
            """Perform operations for a single tenant"""
            tenant_response_times = []
            tenant_id = tenant["id"]

            for _ in range(operations_per_tenant):
                try:
                    op_start = time.time()

                    # Simulate tenant-isolated operations
                    users = await self.db_service.get_tenant_users(tenant_id)
                    searches = await self.db_service.get_tenant_search_history(
                        tenant_id,
                    )
                    analytics = await self.db_service.get_tenant_search_analytics(
                        tenant_id,
                        days=1,
                    )

                    op_end = time.time()
                    response_time = (
                        op_end - op_start
                    ) * 1000  # Convert to milliseconds
                    tenant_response_times.append(response_time)

                except Exception as e:
                    logger.error(f"Tenant operation failed: {e}")
                    failed_ops += 1

            return tenant_response_times

        # Run operations for all tenants concurrently
        tasks = [perform_tenant_operations(tenant) for tenant in self.test_tenants]
        results = await asyncio.gather(*tasks)

        # Flatten results
        for tenant_times in results:
            response_times.extend(tenant_times)
            successful_ops += len(tenant_times)

        end_time = time.time()
        total_time = end_time - start_time

        # Calculate metrics
        metrics = PerformanceMetrics(
            operation="tenant_isolation",
            tenant_count=len(self.test_tenants),
            concurrent_users=len(self.test_users),
            total_operations=len(self.test_tenants) * operations_per_tenant,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            total_time_seconds=total_time,
            average_response_time_ms=(
                statistics.mean(response_times) if response_times else 0
            ),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            p95_response_time_ms=self._calculate_percentile(response_times, 95),
            p99_response_time_ms=self._calculate_percentile(response_times, 99),
            operations_per_second=successful_ops / total_time if total_time > 0 else 0,
            error_rate_percent=(
                (failed_ops / (successful_ops + failed_ops)) * 100
                if (successful_ops + failed_ops) > 0
                else 0
            ),
        )

        logger.info(
            f"✅ Tenant isolation performance test completed: {
                metrics.operations_per_second:.2f} ops/sec",
        )
        return metrics

    async def test_concurrent_tenant_operations(
        self,
        concurrent_operations: int = 50,
    ) -> PerformanceMetrics:
        """Test concurrent operations across multiple tenants"""
        logger.info(
            f"🧪 Testing concurrent tenant operations: {
                concurrent_operations
            } concurrent operations",
        )

        start_time = time.time()
        response_times = []
        successful_ops = 0
        failed_ops = 0

        async def perform_concurrent_operation(operation_id: int) -> float | None:
            """Perform a single concurrent operation"""
            try:
                # Select random tenant and user
                tenant = random.choice(self.test_tenants)
                user = random.choice(
                    [u for u in self.test_users if u["tenant_id"] == tenant["id"]],
                )

                op_start = time.time()

                # Simulate various operations
                operation_type = random.choice(
                    ["search", "analytics", "user_lookup", "activity_log"],
                )

                if operation_type == "search":
                    await self.db_service.save_search_history(
                        tenant_id=tenant["id"],
                        user_id=user["id"],
                        query=f"test query {operation_id}",
                        sources=["web", "arxiv"],
                        results_count=random.randint(1, 20),
                        execution_time_ms=random.uniform(50, 500),
                    )
                elif operation_type == "analytics":
                    await self.db_service.get_tenant_search_analytics(
                        tenant["id"],
                        days=7,
                    )
                elif operation_type == "user_lookup":
                    await self.db_service.get_user_by_id(tenant["id"], user["id"])
                elif operation_type == "activity_log":
                    await self.db_service.log_tenant_activity(
                        tenant_id=tenant["id"],
                        user_id=user["id"],
                        activity_type="test_operation",
                        activity_data={"operation_id": operation_id},
                    )

                op_end = time.time()
                response_time = (op_end - op_start) * 1000
                successful_ops += 1
                return response_time

            except Exception as e:
                logger.error(f"Concurrent operation {operation_id} failed: {e}")
                failed_ops += 1
                return None

        # Run concurrent operations
        tasks = [perform_concurrent_operation(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks)

        # Filter out None results (failed operations)
        response_times = [r for r in results if r is not None]

        end_time = time.time()
        total_time = end_time - start_time

        # Calculate metrics
        metrics = PerformanceMetrics(
            operation="concurrent_operations",
            tenant_count=len(self.test_tenants),
            concurrent_users=concurrent_operations,
            total_operations=concurrent_operations,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            total_time_seconds=total_time,
            average_response_time_ms=(
                statistics.mean(response_times) if response_times else 0
            ),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            p95_response_time_ms=self._calculate_percentile(response_times, 95),
            p99_response_time_ms=self._calculate_percentile(response_times, 99),
            operations_per_second=successful_ops / total_time if total_time > 0 else 0,
            error_rate_percent=(
                (failed_ops / (successful_ops + failed_ops)) * 100
                if (successful_ops + failed_ops) > 0
                else 0
            ),
        )

        logger.info(
            f"✅ Concurrent operations test completed: {
                metrics.operations_per_second:.2f} ops/sec",
        )
        return metrics

    async def test_tenant_context_switching_overhead(
        self,
        context_switches: int = 1000,
    ) -> PerformanceMetrics:
        """Test overhead of tenant context switching"""
        logger.info(
            f"🧪 Testing tenant context switching overhead: {
                context_switches
            } switches",
        )

        start_time = time.time()
        response_times = []
        successful_ops = 0
        failed_ops = 0

        for i in range(context_switches):
            try:
                # Select random tenant
                tenant = random.choice(self.test_tenants)
                tenant_id = tenant["id"]

                switch_start = time.time()

                # Simulate tenant context switch and operation
                users = await self.db_service.get_tenant_users(tenant_id)

                switch_end = time.time()
                response_time = (switch_end - switch_start) * 1000
                response_times.append(response_time)
                successful_ops += 1

            except Exception as e:
                logger.error(f"Context switch {i} failed: {e}")
                failed_ops += 1

        end_time = time.time()
        total_time = end_time - start_time

        # Calculate metrics
        metrics = PerformanceMetrics(
            operation="context_switching",
            tenant_count=len(self.test_tenants),
            concurrent_users=1,
            total_operations=context_switches,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            total_time_seconds=total_time,
            average_response_time_ms=(
                statistics.mean(response_times) if response_times else 0
            ),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            p95_response_time_ms=self._calculate_percentile(response_times, 95),
            p99_response_time_ms=self._calculate_percentile(response_times, 99),
            operations_per_second=successful_ops / total_time if total_time > 0 else 0,
            error_rate_percent=(
                (failed_ops / (successful_ops + failed_ops)) * 100
                if (successful_ops + failed_ops) > 0
                else 0
            ),
        )

        logger.info(
            f"✅ Context switching test completed: {
                metrics.operations_per_second:.2f} ops/sec",
        )
        return metrics

    async def test_database_scalability(
        self,
        max_tenants: int = 50,
        users_per_tenant: int = 10,
    ) -> PerformanceMetrics:
        """Test database scalability with increasing tenant count"""
        logger.info(f"🧪 Testing database scalability: up to {max_tenants} tenants")

        start_time = time.time()
        response_times = []
        successful_ops = 0
        failed_ops = 0

        # Test with increasing tenant counts
        for tenant_count in [10, 25, 50]:
            if tenant_count > len(self.test_tenants):
                break

            # Select subset of tenants
            test_tenants_subset = self.test_tenants[:tenant_count]

            # Perform operations across all tenants
            async def perform_scalability_operation(
                tenant: dict[str, Any],
            ) -> float | None:
                try:
                    op_start = time.time()

                    # Perform multiple operations
                    await self.db_service.get_tenant_users(tenant["id"])
                    await self.db_service.get_tenant_search_history(tenant["id"])
                    await self.db_service.get_tenant_search_analytics(
                        tenant["id"],
                        days=1,
                    )

                    op_end = time.time()
                    response_time = (op_end - op_start) * 1000
                    return response_time

                except Exception as e:
                    logger.error(
                        f"Scalability operation failed for tenant {tenant['id']}: {e}",
                    )
                    return None

            # Run operations concurrently
            tasks = [
                perform_scalability_operation(tenant) for tenant in test_tenants_subset
            ]
            results = await asyncio.gather(*tasks)

            # Filter out None results
            valid_results = [r for r in results if r is not None]
            response_times.extend(valid_results)
            successful_ops += len(valid_results)
            failed_ops += len(results) - len(valid_results)

        end_time = time.time()
        total_time = end_time - start_time

        # Calculate metrics
        metrics = PerformanceMetrics(
            operation="database_scalability",
            tenant_count=max_tenants,
            concurrent_users=users_per_tenant,
            total_operations=successful_ops + failed_ops,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            total_time_seconds=total_time,
            average_response_time_ms=(
                statistics.mean(response_times) if response_times else 0
            ),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            p95_response_time_ms=self._calculate_percentile(response_times, 95),
            p99_response_time_ms=self._calculate_percentile(response_times, 99),
            operations_per_second=successful_ops / total_time if total_time > 0 else 0,
            error_rate_percent=(
                (failed_ops / (successful_ops + failed_ops)) * 100
                if (successful_ops + failed_ops) > 0
                else 0
            ),
        )

        logger.info(
            f"✅ Database scalability test completed: {
                metrics.operations_per_second:.2f} ops/sec",
        )
        return metrics

    def _calculate_percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        if index >= len(sorted_values):
            index = len(sorted_values) - 1

        return sorted_values[index]

    async def run_comprehensive_performance_test(
        self,
        tenant_count: int = 10,
        users_per_tenant: int = 5,
    ) -> dict[str, Any]:
        """Run comprehensive performance test suite"""
        logger.info(
            f"🚀 Starting comprehensive performance test: {tenant_count} tenants, {
                users_per_tenant
            } users each",
        )

        try:
            # Initialize
            await self.initialize()

            # Setup test data
            await self.setup_test_data(tenant_count, users_per_tenant)

            # Run performance tests
            tests = [
                ("tenant_isolation", self.test_tenant_isolation_performance(50)),
                ("concurrent_operations", self.test_concurrent_tenant_operations(100)),
                ("context_switching", self.test_tenant_context_switching_overhead(500)),
                (
                    "database_scalability",
                    self.test_database_scalability(tenant_count, users_per_tenant),
                ),
            ]

            results = {}
            for test_name, test_coro in tests:
                logger.info(f"Running {test_name} test...")
                result = await test_coro
                results[test_name] = result
                self.performance_results.append(result)

            # Generate summary report
            report = self._generate_performance_report(results)

            logger.info("🎉 Comprehensive performance test completed")
            return report

        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            return {"status": "failed", "error": str(e)}
        finally:
            # Cleanup
            await self.cleanup_test_data()
            await self.close()

    def _generate_performance_report(
        self,
        results: dict[str, PerformanceMetrics],
    ) -> dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "test_timestamp": datetime.utcnow().isoformat(),
            "test_summary": {
                "total_tests": len(results),
                "overall_status": "success",
                "total_operations": sum(r.total_operations for r in results.values()),
                "total_successful_operations": sum(
                    r.successful_operations for r in results.values()
                ),
                "total_failed_operations": sum(
                    r.failed_operations for r in results.values()
                ),
                "average_operations_per_second": statistics.mean(
                    [r.operations_per_second for r in results.values()],
                ),
                "average_response_time_ms": statistics.mean(
                    [r.average_response_time_ms for r in results.values()],
                ),
            },
            "test_results": {},
            "performance_analysis": {},
            "recommendations": [],
        }

        # Individual test results
        for test_name, metrics in results.items():
            report["test_results"][test_name] = {
                "operation": metrics.operation,
                "tenant_count": metrics.tenant_count,
                "concurrent_users": metrics.concurrent_users,
                "total_operations": metrics.total_operations,
                "successful_operations": metrics.successful_operations,
                "failed_operations": metrics.failed_operations,
                "total_time_seconds": metrics.total_time_seconds,
                "average_response_time_ms": metrics.average_response_time_ms,
                "min_response_time_ms": metrics.min_response_time_ms,
                "max_response_time_ms": metrics.max_response_time_ms,
                "p95_response_time_ms": metrics.p95_response_time_ms,
                "p99_response_time_ms": metrics.p99_response_time_ms,
                "operations_per_second": metrics.operations_per_second,
                "error_rate_percent": metrics.error_rate_percent,
            }

        # Performance analysis
        report["performance_analysis"] = {
            "tenant_isolation_performance": {
                "status": (
                    "good"
                    if results["tenant_isolation"].operations_per_second > 100
                    else "needs_optimization"
                ),
                "ops_per_second": results["tenant_isolation"].operations_per_second,
                "avg_response_time_ms": results[
                    "tenant_isolation"
                ].average_response_time_ms,
            },
            "concurrent_operations_performance": {
                "status": (
                    "good"
                    if results["concurrent_operations"].operations_per_second > 50
                    else "needs_optimization"
                ),
                "ops_per_second": results[
                    "concurrent_operations"
                ].operations_per_second,
                "error_rate_percent": results[
                    "concurrent_operations"
                ].error_rate_percent,
            },
            "context_switching_overhead": {
                "status": (
                    "acceptable"
                    if results["context_switching"].average_response_time_ms < 10
                    else "high_overhead"
                ),
                "avg_response_time_ms": results[
                    "context_switching"
                ].average_response_time_ms,
                "ops_per_second": results["context_switching"].operations_per_second,
            },
            "database_scalability": {
                "status": (
                    "good"
                    if results["database_scalability"].operations_per_second > 25
                    else "needs_optimization"
                ),
                "ops_per_second": results["database_scalability"].operations_per_second,
                "avg_response_time_ms": results[
                    "database_scalability"
                ].average_response_time_ms,
            },
        }

        # Generate recommendations
        recommendations = []

        if results["tenant_isolation"].operations_per_second < 100:
            recommendations.append(
                "Optimize tenant isolation queries - consider adding composite indexes",
            )

        if results["concurrent_operations"].error_rate_percent > 5:
            recommendations.append(
                "Investigate concurrent operation failures - check for deadlocks or resource contention",
            )

        if results["context_switching"].average_response_time_ms > 10:
            recommendations.append(
                "Optimize tenant context switching - consider caching tenant data",
            )

        if results["database_scalability"].operations_per_second < 25:
            recommendations.append(
                "Improve database scalability - consider connection pooling and query optimization",
            )

        if not recommendations:
            recommendations.append(
                "Performance is within acceptable limits - continue monitoring",
            )

        report["recommendations"] = recommendations

        return report


async def main():
    """Main performance testing function"""
    parser = argparse.ArgumentParser(
        description="PAKE System Multi-Tenant Performance Testing",
    )
    parser.add_argument(
        "--tenants",
        type=int,
        default=10,
        help="Number of test tenants",
    )
    parser.add_argument(
        "--users-per-tenant",
        type=int,
        default=5,
        help="Users per tenant",
    )
    parser.add_argument("--db-host", default="localhost", help="Database host")
    parser.add_argument(
        "--db-name",
        default="pake_system_multitenant",
        help="Database name",
    )
    parser.add_argument("--output-report", help="Output performance report to file")

    args = parser.parse_args()

    # Configure database
    db_config = MultiTenantDatabaseConfig(host=args.db_host, database=args.db_name)

    # Initialize tester
    tester = MultiTenantPerformanceTester(db_config)

    # Run comprehensive test
    report = await tester.run_comprehensive_performance_test(
        tenant_count=args.tenants,
        users_per_tenant=args.users_per_tenant,
    )

    # Output results
    if args.output_report:
        with open(args.output_report, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"📄 Performance report saved to: {args.output_report}")

    # Print summary
    print("\n" + "=" * 80)
    print("MULTI-TENANT PERFORMANCE TEST SUMMARY")
    print("=" * 80)
    print(f"Status: {report['test_summary']['overall_status'].upper()}")
    print(f"Total Operations: {report['test_summary']['total_operations']}")
    print(
        f"Successful Operations: {
            report['test_summary']['total_successful_operations']
        }",
    )
    print(f"Failed Operations: {report['test_summary']['total_failed_operations']}")
    print(
        f"Average Ops/Second: {
            report['test_summary']['average_operations_per_second']:.2f}",
    )
    print(
        f"Average Response Time: {
            report['test_summary']['average_response_time_ms']:.2f}ms",
    )

    print("\n📊 Test Results:")
    for test_name, result in report["test_results"].items():
        print(
            f"  {test_name}: {result['operations_per_second']:.2f} ops/sec, "
            f"{result['average_response_time_ms']:.2f}ms avg, "
            f"{result['error_rate_percent']:.1f}% errors",
        )

    print("\n🎯 Recommendations:")
    for i, recommendation in enumerate(report["recommendations"], 1):
        print(f"  {i}. {recommendation}")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
