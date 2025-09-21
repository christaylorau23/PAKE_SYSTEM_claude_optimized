"""
TDD Tests for Performance Benchmarking System
Following Test-Driven Development principles
"""

import asyncio
import time
from dataclasses import asdict
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Note: These tests are written FIRST following TDD principles
# Implementation should follow to make these tests pass


@pytest.mark.performance
@pytest.mark.unit
class TestPerformanceBenchmark:
    """Test suite for Performance Benchmarking System"""

    @pytest.fixture
    def benchmark_config(self, performance_benchmark_config):
        """Configuration for performance benchmark testing."""
        return performance_benchmark_config

    @pytest.fixture
    def mock_aiohttp_session(self):
        """Mock aiohttp session for testing."""
        session = MagicMock()
        response = MagicMock()
        response.status = 200
        response.text = AsyncMock(return_value='{"status": "ok"}')
        session.get.return_value.__aenter__.return_value = response
        session.post.return_value.__aenter__.return_value = response
        return session

    def test_performance_benchmark_initialization(self, benchmark_config):
        """Test performance benchmark initializes correctly."""
        from scripts.performance_benchmark import PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])

        assert benchmark.base_url == benchmark_config["base_url"]
        assert benchmark.results == []
        assert benchmark.resource_usage == []
        assert benchmark.session is None  # Not started yet

    def test_system_resource_monitoring(self, benchmark_config):
        """Test system resource usage measurement."""
        from scripts.performance_benchmark import (
            PerformanceBenchmark,
            SystemResourceUsage,
        )

        benchmark = PerformanceBenchmark()

        usage = benchmark.get_system_resources()

        assert isinstance(usage, SystemResourceUsage)
        assert 0.0 <= usage.cpu_percent <= 100.0
        assert usage.memory_used_mb > 0
        assert usage.memory_available_mb > 0
        assert 0.0 <= usage.memory_percent <= 100.0
        assert 0.0 <= usage.disk_usage_percent <= 100.0
        assert usage.network_io_bytes >= 0
        assert usage.timestamp is not None

    @pytest.mark.asyncio
    async def test_single_endpoint_benchmark(
        self,
        benchmark_config,
        mock_aiohttp_session,
    ):
        """Test benchmarking of a single API endpoint."""
        from scripts.performance_benchmark import BenchmarkResult, PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])
        benchmark.session = mock_aiohttp_session

        result = await benchmark.benchmark_endpoint(
            test_name="Health Check Test",
            endpoint="/health",
            method="GET",
        )

        assert isinstance(result, BenchmarkResult)
        assert result.test_name == "Health Check Test"
        assert result.endpoint == "/health"
        assert result.method == "GET"
        assert result.duration_ms > 0
        assert result.status_code == 200
        assert result.success
        assert result.response_size_bytes > 0
        assert result.timestamp is not None

    @pytest.mark.asyncio
    async def test_post_endpoint_benchmark(
        self,
        benchmark_config,
        mock_aiohttp_session,
    ):
        """Test benchmarking of POST endpoints with payload."""
        from scripts.performance_benchmark import PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])
        benchmark.session = mock_aiohttp_session

        payload = {"query": "test search", "sources": ["web"]}

        result = await benchmark.benchmark_endpoint(
            test_name="Search API Test",
            endpoint="/search",
            method="POST",
            payload=payload,
        )

        assert result.test_name == "Search API Test"
        assert result.method == "POST"
        assert result.success
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_load_testing_concurrent_requests(
        self,
        benchmark_config,
        mock_aiohttp_session,
    ):
        """Test load testing with concurrent requests."""
        from scripts.performance_benchmark import PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])
        benchmark.session = mock_aiohttp_session

        results = await benchmark.run_load_test(
            test_name="Concurrent Load Test",
            endpoint="/health",
            method="GET",
            concurrent_requests=5,
            total_requests=20,
        )

        assert len(results) == 20
        assert all(isinstance(result, type(results[0])) for result in results)
        assert all(result.test_name == "Concurrent Load Test" for result in results)

        # Check that system resources were recorded
        assert len(benchmark.resource_usage) >= 2  # Start and end measurements

    def test_performance_metrics_calculation(self, benchmark_config):
        """Test calculation of performance metrics from benchmark results."""
        from scripts.performance_benchmark import (
            BenchmarkResult,
            PerformanceBenchmark,
            PerformanceMetrics,
        )

        benchmark = PerformanceBenchmark()

        # Create sample results
        sample_results = [
            BenchmarkResult(
                test_name="Test",
                endpoint="/test",
                method="GET",
                duration_ms=100.0,
                status_code=200,
                response_size_bytes=1000,
                success=True,
                timestamp=datetime.now().isoformat(),
            ),
            BenchmarkResult(
                test_name="Test",
                endpoint="/test",
                method="GET",
                duration_ms=150.0,
                status_code=200,
                response_size_bytes=1200,
                success=True,
                timestamp=datetime.now().isoformat(),
            ),
            BenchmarkResult(
                test_name="Test",
                endpoint="/test",
                method="GET",
                duration_ms=80.0,
                status_code=500,
                response_size_bytes=500,
                success=False,
                timestamp=datetime.now().isoformat(),
            ),
        ]

        metrics = benchmark.calculate_metrics(sample_results)

        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.total_tests == 3
        assert metrics.successful_tests == 2
        assert metrics.failed_tests == 1
        assert metrics.success_rate == 2 / 3 * 100
        assert metrics.min_duration_ms == 100.0  # Only successful tests
        assert metrics.max_duration_ms == 150.0
        assert 100.0 <= metrics.avg_duration_ms <= 150.0

    @pytest.mark.asyncio
    async def test_comprehensive_benchmark_suite(
        self,
        benchmark_config,
        mock_aiohttp_session,
    ):
        """Test comprehensive benchmark suite execution."""
        from scripts.performance_benchmark import PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])
        benchmark.session = mock_aiohttp_session

        results = await benchmark.run_comprehensive_benchmark()

        assert isinstance(results, dict)
        assert len(results) > 0

        # Check that all expected test categories are present
        expected_tests = [
            "Health Check",
            "Quick Search",
            "Multi-source Search",
            "System Health Analytics",
        ]
        for test_name in expected_tests:
            assert any(test_name in key for key in results.keys())

        # Validate result structure
        for test_name, test_data in results.items():
            assert "metrics" in test_data
            assert "raw_results" in test_data
            assert test_data["metrics"]["total_tests"] > 0

    def test_benchmark_report_generation(self, benchmark_config):
        """Test performance benchmark report generation."""
        from scripts.performance_benchmark import (
            PerformanceBenchmark,
            PerformanceMetrics,
        )

        benchmark = PerformanceBenchmark()

        # Mock results data
        sample_results = {
            "Health Check": {
                "metrics": asdict(
                    PerformanceMetrics(
                        test_name="Health Check",
                        total_tests=10,
                        successful_tests=10,
                        failed_tests=0,
                        avg_duration_ms=85.5,
                        min_duration_ms=75.0,
                        max_duration_ms=95.0,
                        median_duration_ms=85.0,
                        p95_duration_ms=93.0,
                        p99_duration_ms=95.0,
                        success_rate=100.0,
                        avg_response_size_bytes=1000,
                        throughput_per_second=11.7,
                        system_cpu_percent=45.2,
                        system_memory_percent=67.8,
                    ),
                ),
                "raw_results": [],
            },
        }

        report = benchmark.generate_report(sample_results)

        assert isinstance(report, str)
        assert "Performance Benchmark Report" in report
        assert "Performance Summary" in report
        assert "Health Check" in report
        assert "85.5ms" in report  # Average duration
        assert "100.0%" in report  # Success rate
        assert "Performance Recommendations" in report

    @pytest.mark.asyncio
    async def test_error_handling_and_timeouts(self, benchmark_config):
        """Test error handling for failed requests and timeouts."""
        from scripts.performance_benchmark import BenchmarkResult, PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])

        # Mock session that raises an exception
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection timeout")
        benchmark.session = mock_session

        result = await benchmark.benchmark_endpoint(
            test_name="Timeout Test",
            endpoint="/slow-endpoint",
            method="GET",
        )

        assert isinstance(result, BenchmarkResult)
        assert result.success == False
        assert result.error_message is not None
        assert "timeout" in result.error_message.lower()
        assert result.status_code == 0
        assert result.duration_ms > 0  # Should still measure time taken

    def test_performance_thresholds_validation(self, benchmark_config):
        """Test performance threshold validation and alerting."""
        from scripts.performance_benchmark import (
            PerformanceBenchmark,
            PerformanceMetrics,
        )

        benchmark = PerformanceBenchmark()

        # Create metrics that exceed thresholds
        slow_metrics = PerformanceMetrics(
            test_name="Slow Test",
            total_tests=10,
            successful_tests=8,
            failed_tests=2,
            avg_duration_ms=1500.0,  # Very slow
            min_duration_ms=1000.0,
            max_duration_ms=2000.0,
            median_duration_ms=1500.0,
            p95_duration_ms=1900.0,
            p99_duration_ms=2000.0,
            success_rate=80.0,  # Low success rate
            avg_response_size_bytes=5000,
            throughput_per_second=0.67,
            system_cpu_percent=85.0,
            system_memory_percent=92.0,
        )

        issues = benchmark.identify_performance_issues(slow_metrics)

        assert len(issues) > 0
        assert any("slow" in issue.lower() for issue in issues)
        assert any("success rate" in issue.lower() for issue in issues)
        assert any("resource" in issue.lower() for issue in issues)

    @pytest.mark.asyncio
    async def test_real_time_monitoring_integration(self, benchmark_config):
        """Test integration with real-time monitoring systems."""
        from scripts.performance_benchmark import PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])

        # Mock real-time monitoring callback
        monitoring_data = []

        def monitoring_callback(result):
            monitoring_data.append(
                {
                    "timestamp": result.timestamp,
                    "endpoint": result.endpoint,
                    "duration": result.duration_ms,
                    "success": result.success,
                },
            )

        benchmark.set_monitoring_callback(monitoring_callback)

        # Run a test with monitoring
        await benchmark.benchmark_endpoint(
            test_name="Monitored Test",
            endpoint="/health",
            method="GET",
        )

        assert len(monitoring_data) == 1
        assert monitoring_data[0]["endpoint"] == "/health"

    def test_benchmark_configuration_validation(self, benchmark_config):
        """Test benchmark configuration validation."""
        from scripts.performance_benchmark import PerformanceBenchmark

        # Test invalid base URL
        with pytest.raises(ValueError, match="Invalid base URL"):
            PerformanceBenchmark("")

        # Test invalid concurrent requests
        benchmark = PerformanceBenchmark("http://localhost:8000")

        with pytest.raises(ValueError, match="concurrent_requests must be positive"):
            asyncio.run(
                benchmark.run_load_test(
                    "Test",
                    "/health",
                    "GET",
                    concurrent_requests=0,
                    total_requests=10,
                ),
            )

    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self, benchmark_config):
        """Test memory usage monitoring during benchmarks."""
        import psutil

        from scripts.performance_benchmark import PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])

        initial_memory = psutil.Process().memory_info().rss

        # Run memory-intensive benchmark
        await benchmark.run_memory_benchmark(iterations=100)

        final_memory = psutil.Process().memory_info().rss
        memory_growth = final_memory - initial_memory

        # Should track memory usage
        assert hasattr(benchmark, "memory_snapshots")
        assert len(benchmark.memory_snapshots) > 0

        # Memory growth should be reasonable (not a memory leak)
        assert memory_growth < 100 * 1024 * 1024  # Less than 100MB growth

    @pytest.mark.asyncio
    async def test_database_performance_benchmarking(self, benchmark_config):
        """Test database performance benchmarking capabilities."""
        from scripts.performance_benchmark import PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])

        # Mock database operations
        db_operations = [
            {"operation": "SELECT", "query": "SELECT * FROM users LIMIT 100"},
            {
                "operation": "INSERT",
                "query": "INSERT INTO logs (message) VALUES ('test')",
            },
            {"operation": "UPDATE", "query": "UPDATE users SET last_login = NOW()"},
            {
                "operation": "DELETE",
                "query": "DELETE FROM temp_data WHERE created < NOW() - INTERVAL '1 day'",
            },
        ]

        results = await benchmark.benchmark_database_operations(db_operations)

        assert len(results) == len(db_operations)
        assert all("duration_ms" in result for result in results)
        assert all("success" in result for result in results)
        assert all(
            result["operation"] in ["SELECT", "INSERT", "UPDATE", "DELETE"]
            for result in results
        )

    @pytest.mark.asyncio
    async def test_cache_performance_benchmarking(self, benchmark_config):
        """Test cache performance benchmarking."""
        from scripts.performance_benchmark import PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])

        cache_tests = [
            {"operation": "SET", "key": "test_key", "value": "test_value"},
            {"operation": "GET", "key": "test_key"},
            {"operation": "DELETE", "key": "test_key"},
            {
                "operation": "PIPELINE",
                "commands": ["SET key1 val1", "SET key2 val2", "GET key1"],
            },
        ]

        results = await benchmark.benchmark_cache_operations(cache_tests)

        assert len(results) == len(cache_tests)
        assert all(
            "cache_hit_rate" in result
            for result in results
            if result["operation"] == "GET"
        )
        assert all("latency_ms" in result for result in results)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_system_benchmark(self, benchmark_config):
        """Test full system performance benchmark integration."""
        from scripts.performance_benchmark import PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])

        # Run comprehensive system benchmark
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"status": "healthy"}')
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session

            async with benchmark:
                results = await benchmark.run_comprehensive_benchmark()
                report = benchmark.generate_report(results)

        # Validate comprehensive results
        assert len(results) >= 5  # Multiple test categories
        assert len(report) > 1000  # Comprehensive report

        # Check performance analysis
        assert "Performance Summary" in report
        assert "Recommendations" in report

        # Verify system resource tracking
        assert len(benchmark.resource_usage) > 0

    def test_benchmark_results_persistence(self, benchmark_config, tmp_path):
        """Test benchmark results persistence and loading."""

        from scripts.performance_benchmark import PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])

        # Create sample results
        results = {
            "Health Check": {
                "metrics": {"avg_duration_ms": 85.5, "success_rate": 100.0},
                "raw_results": [],
            },
        }

        # Save results
        results_file = tmp_path / "benchmark_results.json"
        benchmark.save_results(results, str(results_file))

        assert results_file.exists()

        # Load and verify results
        loaded_results = benchmark.load_results(str(results_file))
        assert loaded_results["Health Check"]["metrics"]["avg_duration_ms"] == 85.5

    @pytest.mark.performance
    def test_benchmark_execution_performance(self, benchmark_config):
        """Test that benchmark execution itself is performant."""
        from scripts.performance_benchmark import PerformanceBenchmark

        benchmark = PerformanceBenchmark(benchmark_config["base_url"])

        # Test overhead of benchmark framework itself
        start_time = time.time()

        # Simulate lightweight operations
        for _ in range(100):
            usage = benchmark.get_system_resources()
            assert usage is not None

        execution_time = time.time() - start_time

        # Benchmark framework should have minimal overhead
        assert execution_time < 5.0  # Under 5 seconds for 100 measurements
        # Shouldn't auto-store unless explicitly called
        assert len(benchmark.resource_usage) == 0
