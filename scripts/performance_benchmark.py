#!/usr/bin/env python3
"""
PAKE System - Comprehensive Performance Benchmarking Suite
Enterprise-grade performance testing and optimization analysis
"""

import asyncio
import json
import logging
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
import psutil

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))


@dataclass
class BenchmarkResult:
    """Individual benchmark test result"""

    test_name: str
    endpoint: str
    method: str
    duration_ms: float
    status_code: int
    response_size_bytes: int
    success: bool
    error_message: str | None = None
    timestamp: str = ""


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics"""

    test_name: str
    total_tests: int
    successful_tests: int
    failed_tests: int
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    median_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    success_rate: float
    avg_response_size_bytes: int
    throughput_per_second: float
    system_cpu_percent: float
    system_memory_percent: float


@dataclass
class SystemResourceUsage:
    """System resource usage during benchmark"""

    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    network_io_bytes: int
    timestamp: str


class PerformanceBenchmark:
    """Comprehensive performance benchmarking suite"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.results: list[BenchmarkResult] = []
        self.resource_usage: list[SystemResourceUsage] = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def get_system_resources(self) -> SystemResourceUsage:
        """Get current system resource usage"""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return SystemResourceUsage(
            cpu_percent=psutil.cpu_percent(),
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            memory_available_mb=memory.available / (1024 * 1024),
            disk_usage_percent=disk.percent,
            network_io_bytes=sum(psutil.net_io_counters()._asdict().values()),
            timestamp=datetime.now().isoformat(),
        )

    async def benchmark_endpoint(
        self,
        test_name: str,
        endpoint: str,
        method: str = "GET",
        payload: dict | None = None,
        headers: dict | None = None,
    ) -> BenchmarkResult:
        """Benchmark a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    status_code = response.status
            elif method.upper() == "POST":
                async with self.session.post(
                    url,
                    json=payload,
                    headers=headers,
                ) as response:
                    response_text = await response.text()
                    status_code = response.status
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            duration_ms = (time.time() - start_time) * 1000
            response_size_bytes = len(response_text.encode("utf-8"))

            return BenchmarkResult(
                test_name=test_name,
                endpoint=endpoint,
                method=method,
                duration_ms=duration_ms,
                status_code=status_code,
                response_size_bytes=response_size_bytes,
                success=200 <= status_code < 300,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return BenchmarkResult(
                test_name=test_name,
                endpoint=endpoint,
                method=method,
                duration_ms=duration_ms,
                status_code=0,
                response_size_bytes=0,
                success=False,
                error_message=str(e),
                timestamp=datetime.now().isoformat(),
            )

    async def run_load_test(
        self,
        test_name: str,
        endpoint: str,
        method: str = "GET",
        payload: dict | None = None,
        concurrent_requests: int = 10,
        total_requests: int = 100,
    ) -> list[BenchmarkResult]:
        """Run load test with concurrent requests"""
        logger.info(
            f"Running load test: {test_name} ({concurrent_requests} concurrent, {
                total_requests
            } total)",
        )

        # Record system resources at start
        self.resource_usage.append(self.get_system_resources())

        semaphore = asyncio.Semaphore(concurrent_requests)

        async def make_request():
            async with semaphore:
                return await self.benchmark_endpoint(
                    test_name,
                    endpoint,
                    method,
                    payload,
                )

        # Create tasks for concurrent execution
        tasks = [make_request() for _ in range(total_requests)]

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and convert to BenchmarkResult
        valid_results = []
        for result in results:
            if isinstance(result, BenchmarkResult):
                valid_results.append(result)
            else:
                # Handle exceptions
                valid_results.append(
                    BenchmarkResult(
                        test_name=test_name,
                        endpoint=endpoint,
                        method=method,
                        duration_ms=0,
                        status_code=0,
                        response_size_bytes=0,
                        success=False,
                        error_message=str(result),
                        timestamp=datetime.now().isoformat(),
                    ),
                )

        # Record system resources at end
        self.resource_usage.append(self.get_system_resources())

        return valid_results

    def calculate_metrics(self, results: list[BenchmarkResult]) -> PerformanceMetrics:
        """Calculate performance metrics from benchmark results"""
        if not results:
            return PerformanceMetrics(
                test_name="empty",
                total_tests=0,
                successful_tests=0,
                failed_tests=0,
                avg_duration_ms=0,
                min_duration_ms=0,
                max_duration_ms=0,
                median_duration_ms=0,
                p95_duration_ms=0,
                p99_duration_ms=0,
                success_rate=0,
                avg_response_size_bytes=0,
                throughput_per_second=0,
                system_cpu_percent=0,
                system_memory_percent=0,
            )

        durations = [r.duration_ms for r in results if r.success]
        response_sizes = [r.response_size_bytes for r in results if r.success]

        successful_tests = len([r for r in results if r.success])
        failed_tests = len(results) - successful_tests

        # Calculate percentiles
        durations_sorted = sorted(durations) if durations else [0]
        p95_index = int(len(durations_sorted) * 0.95)
        p99_index = int(len(durations_sorted) * 0.99)

        # System resource usage
        cpu_percent = (
            statistics.mean([r.cpu_percent for r in self.resource_usage])
            if self.resource_usage
            else 0
        )
        memory_percent = (
            statistics.mean([r.memory_percent for r in self.resource_usage])
            if self.resource_usage
            else 0
        )

        return PerformanceMetrics(
            test_name=results[0].test_name if results else "unknown",
            total_tests=len(results),
            successful_tests=successful_tests,
            failed_tests=failed_tests,
            avg_duration_ms=statistics.mean(durations) if durations else 0,
            min_duration_ms=min(durations) if durations else 0,
            max_duration_ms=max(durations) if durations else 0,
            median_duration_ms=statistics.median(durations) if durations else 0,
            p95_duration_ms=durations_sorted[p95_index] if durations_sorted else 0,
            p99_duration_ms=durations_sorted[p99_index] if durations_sorted else 0,
            success_rate=(successful_tests / len(results)) * 100 if results else 0,
            avg_response_size_bytes=(
                int(statistics.mean(response_sizes)) if response_sizes else 0
            ),
            throughput_per_second=(
                successful_tests / (max(durations) / 1000) if durations else 0
            ),
            system_cpu_percent=cpu_percent,
            system_memory_percent=memory_percent,
        )

    async def run_comprehensive_benchmark(self) -> dict[str, Any]:
        """Run comprehensive benchmark suite"""
        logger.info("Starting comprehensive performance benchmark suite")

        benchmark_tests = [
            # Health and Status Endpoints
            ("Health Check", "/health", "GET"),
            # Search Endpoints
            (
                "Quick Search",
                "/quick",
                "POST",
                {"query": "machine learning algorithms", "enable_ml_enhancement": True},
            ),
            (
                "Multi-source Search",
                "/search",
                "POST",
                {
                    "query": "artificial intelligence research",
                    "sources": ["web", "arxiv", "pubmed"],
                    "max_results": 10,
                    "enable_ml_enhancement": True,
                },
            ),
            # Analytics Endpoints
            ("System Health Analytics", "/analytics/system-health", "GET"),
            ("Comprehensive Report", "/analytics/comprehensive-report", "GET"),
            ("Insights", "/analytics/insights", "GET"),
            ("Anomaly Detection", "/analytics/anomalies", "GET"),
            # ML Services
            (
                "Auto-tagging",
                "/ml/auto-tag",
                "POST",
                {
                    "content": "This document discusses machine learning and artificial intelligence applications",
                    "max_tags": 5,
                },
            ),
            (
                "Metadata Extraction",
                "/ml/extract-metadata",
                "POST",
                {
                    "content": "Dr. John Smith published a groundbreaking paper on AI at https://arxiv.org/abs/2023.12345",
                    "include_entities": True,
                    "include_topics": True,
                    "include_sentiment": True,
                },
            ),
            # Knowledge Graph
            ("Knowledge Graph", "/knowledge-graph", "GET"),
            # Obsidian Integration
            (
                "Obsidian Sync",
                "/obsidian/sync",
                "POST",
                {
                    "event": {
                        "type": "create",
                        "filepath": "/test/file.md",
                        "timestamp": datetime.now().isoformat(),
                    },
                    "vault_path": "/test/vault",
                },
            ),
        ]

        all_results = {}

        for test_config in benchmark_tests:
            test_name = test_config[0]
            endpoint = test_config[1]
            method = test_config[2]
            payload = test_config[3] if len(test_config) > 3 else None

            logger.info(f"Running benchmark: {test_name}")

            # Run load test
            results = await self.run_load_test(
                test_name=test_name,
                endpoint=endpoint,
                method=method,
                payload=payload,
                concurrent_requests=5,
                total_requests=20,
            )

            # Calculate metrics
            metrics = self.calculate_metrics(results)
            all_results[test_name] = {
                "metrics": asdict(metrics),
                "raw_results": [
                    asdict(r) for r in results[:5]
                ],  # Store first 5 results
            }

            logger.info(
                f"Completed {test_name}: {metrics.success_rate:.1f}% success rate, {
                    metrics.avg_duration_ms:.1f}ms avg",
            )

        return all_results

    def generate_report(self, results: dict[str, Any]) -> str:
        """Generate comprehensive performance report"""
        report = []
        report.append("# PAKE System Performance Benchmark Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary table
        report.append("## Performance Summary")
        report.append("")
        report.append(
            "| Test | Success Rate | Avg Duration | P95 Duration | Throughput/sec |",
        )
        report.append(
            "|------|-------------|--------------|--------------|----------------|",
        )

        for test_name, data in results.items():
            metrics = data["metrics"]
            report.append(
                f"| {test_name} | {metrics['success_rate']:.1f}% | {
                    metrics['avg_duration_ms']:.1f}ms | {
                    metrics['p95_duration_ms']:.1f}ms | {
                    metrics['throughput_per_second']:.1f} |",
            )

        report.append("")

        # Detailed analysis
        report.append("## Detailed Analysis")
        report.append("")

        for test_name, data in results.items():
            metrics = data["metrics"]
            report.append(f"### {test_name}")
            report.append("")
            report.append(f"- **Total Tests**: {metrics['total_tests']}")
            report.append(f"- **Successful**: {metrics['successful_tests']}")
            report.append(f"- **Failed**: {metrics['failed_tests']}")
            report.append(f"- **Success Rate**: {metrics['success_rate']:.1f}%")
            report.append(f"- **Average Duration**: {metrics['avg_duration_ms']:.1f}ms")
            report.append(
                f"- **Median Duration**: {metrics['median_duration_ms']:.1f}ms",
            )
            report.append(f"- **95th Percentile**: {metrics['p95_duration_ms']:.1f}ms")
            report.append(f"- **99th Percentile**: {metrics['p99_duration_ms']:.1f}ms")
            report.append(f"- **Min Duration**: {metrics['min_duration_ms']:.1f}ms")
            report.append(f"- **Max Duration**: {metrics['max_duration_ms']:.1f}ms")
            report.append(
                f"- **Average Response Size**: {metrics['avg_response_size_bytes']} bytes",
            )
            report.append(
                f"- **Throughput**: {metrics['throughput_per_second']:.1f} requests/second",
            )
            report.append("")

        # System resources
        if self.resource_usage:
            report.append("## System Resource Usage")
            report.append("")
            avg_cpu = statistics.mean([r.cpu_percent for r in self.resource_usage])
            avg_memory = statistics.mean(
                [r.memory_percent for r in self.resource_usage],
            )
            report.append(f"- **Average CPU Usage**: {avg_cpu:.1f}%")
            report.append(f"- **Average Memory Usage**: {avg_memory:.1f}%")
            report.append("")

        # Recommendations
        report.append("## Performance Recommendations")
        report.append("")

        # Analyze results and provide recommendations
        slow_endpoints = []
        low_success_endpoints = []

        for test_name, data in results.items():
            metrics = data["metrics"]
            if metrics["avg_duration_ms"] > 1000:  # Slower than 1 second
                slow_endpoints.append((test_name, metrics["avg_duration_ms"]))
            if metrics["success_rate"] < 95:  # Less than 95% success rate
                low_success_endpoints.append((test_name, metrics["success_rate"]))

        if slow_endpoints:
            report.append("### Performance Optimization Needed")
            report.append("The following endpoints are slower than 1 second:")
            for endpoint, duration in slow_endpoints:
                report.append(f"- **{endpoint}**: {duration:.1f}ms average")
            report.append("")

        if low_success_endpoints:
            report.append("### Reliability Issues")
            report.append("The following endpoints have low success rates:")
            for endpoint, success_rate in low_success_endpoints:
                report.append(f"- **{endpoint}**: {success_rate:.1f}% success rate")
            report.append("")

        report.append("### General Recommendations")
        report.append(
            "1. **Caching**: Implement Redis caching for frequently accessed data",
        )
        report.append(
            "2. **Database Optimization**: Review and optimize database queries",
        )
        report.append(
            "3. **Async Processing**: Ensure all I/O operations are properly async",
        )
        report.append(
            "4. **Resource Monitoring**: Implement continuous performance monitoring",
        )
        report.append(
            "5. **Load Balancing**: Consider horizontal scaling for high-traffic endpoints",
        )

        return "\n".join(report)


async def main():
    """Main benchmark execution"""
    logger.info("Starting PAKE System Performance Benchmark")

    async with PerformanceBenchmark() as benchmark:
        # Run comprehensive benchmark
        results = await benchmark.run_comprehensive_benchmark()

        # Generate report
        report = benchmark.generate_report(results)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON results
        results_file = f"performance_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {results_file}")

        # Save markdown report
        report_file = f"performance_report_{timestamp}.md"
        with open(report_file, "w") as f:
            f.write(report)
        logger.info(f"Report saved to {report_file}")

        # Print summary
        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 60)
        print(report)
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
