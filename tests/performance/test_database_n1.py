#!/usr/bin/env python3
"""
PAKE System - Database N+1 Query Tests
Phase 5: Performance Under Pressure

These tests validate that eager loading is properly implemented and
N+1 queries have been eliminated from the codebase.

Test Strategy:
1. Count SQL queries executed during operations
2. Compare lazy loading (N+1) vs eager loading query counts
3. Validate that eager loading reduces queries by 50-90%
4. Assert that list operations use ≤3 queries regardless of result size
"""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.services.base.models import (
    ServiceHealthCheck,
    ServiceMetrics,
    ServiceRegistry,
)
from src.services.repositories.optimized_queries import OptimizedServiceQueries


class QueryCounter:
    """
    Context manager to count SQL queries executed during a code block.

    Usage:
        with QueryCounter(session) as counter:
            # Execute code
            ...
        print(f"Executed {counter.count} queries")
    """

    def __init__(self, session):
        self.session = session
        self.count = 0
        self.queries = []

    def __enter__(self):
        """Register query counter when entering context"""
        event.listen(self.session.bind, "after_cursor_execute", self._count_query)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Unregister query counter when exiting context"""
        event.remove(self.session.bind, "after_cursor_execute", self._count_query)

    def _count_query(self, conn, cursor, statement, parameters, context, executemany):
        """Callback to count each query"""
        self.count += 1
        self.queries.append(statement)


@pytest.fixture()
def test_db_session():
    """Create a test database session with in-memory SQLite"""
    from src.services.base.database import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


@pytest.fixture()
def sample_services(test_db_session):
    """Create sample services with health checks and metrics"""
    services = []

    for i in range(5):
        service = ServiceRegistry(
            service_id=uuid4(),
            service_name=f"service-{i}",
            service_version="1.0.0",
            service_type="api",
            environment="test",
            base_url=f"http://service-{i}:8000",
            health_check_url=f"http://service-{i}:8000/health",
        )
        test_db_session.add(service)
        services.append(service)

        # Add health checks for each service
        for j in range(3):
            health_check = ServiceHealthCheck(
                health_check_id=uuid4(),
                service_id=service.service_id,
                status="HEALTHY",
                response_time_ms=100.0 + j * 10,
                check_type="HTTP",
            )
            test_db_session.add(health_check)

        # Add metrics for each service
        for k in range(2):
            metric = ServiceMetrics(
                metric_id=uuid4(),
                service_id=service.service_id,
                metric_name=f"metric_{k}",
                metric_value=100.0 + k * 50,
            )
            test_db_session.add(metric)

    test_db_session.commit()
    return services


@pytest.mark.unit()
@pytest.mark.unit_performance()
def test_n1_problem_lazy_loading(test_db_session, sample_services):
    """
    Test demonstrating N+1 query problem with lazy loading.

    Expected behavior:
    - 1 query to fetch services
    - N queries to fetch health checks (one per service access)
    - Total: N + 1 queries

    This test documents the problem we're solving with eager loading.
    """
    from sqlalchemy import select

    with QueryCounter(test_db_session) as counter:
        # 1 query to fetch services
        services = (
            test_db_session.execute(select(ServiceRegistry).limit(5)).scalars().all()
        )

        # N queries (one per service when accessing health_checks)
        for service in services:
            _ = service.health_checks  # Triggers lazy loading query

    # Should be N + 1 queries (5 + 1 = 6)
    assert counter.count == 6, (
        f"Expected 6 queries with lazy loading (N+1 problem), " f"got {counter.count}"
    )


@pytest.mark.unit()
@pytest.mark.unit_performance()
def test_eager_loading_eliminates_n1(test_db_session, sample_services):
    """
    Test that eager loading eliminates N+1 queries.

    Expected behavior:
    - 1 query to fetch services
    - 1 query to fetch all health checks using WHERE IN
    - Total: 2 queries (regardless of N)
    """
    with QueryCounter(test_db_session) as counter:
        services = OptimizedServiceQueries.list_services_with_health_checks(
            test_db_session, limit=5
        )

        # Access health_checks - no additional queries!
        for service in services:
            _ = service.health_checks  # Already loaded, no query

    # Should be exactly 2 queries
    assert counter.count == 2, (
        f"Expected 2 queries with eager loading, got {counter.count}. "
        f"Queries: {counter.queries}"
    )


@pytest.mark.unit()
@pytest.mark.unit_performance()
def test_eager_loading_all_relationships(test_db_session, sample_services):
    """
    Test eager loading multiple relationships simultaneously.

    Expected behavior:
    - 1 query to fetch services
    - 1 query to fetch all health checks
    - 1 query to fetch all metrics
    - Total: 3 queries (regardless of N)
    """
    with QueryCounter(test_db_session) as counter:
        services = OptimizedServiceQueries.list_services_with_all_relationships(
            test_db_session, limit=5
        )

        # Access all relationships - no additional queries!
        for service in services:
            _ = service.health_checks  # Already loaded
            _ = service.metrics  # Already loaded

    # Should be exactly 3 queries
    assert (
        counter.count == 3
    ), f"Expected 3 queries with eager loading, got {counter.count}"


@pytest.mark.unit()
@pytest.mark.unit_performance()
def test_joinedload_many_to_one(test_db_session, sample_services):
    """
    Test joinedload for many-to-one relationships.

    When fetching a child object and its parent, joinedload
    should use a single query with JOIN instead of two queries.

    Expected: 1 query (vs 2 with lazy loading)
    """
    # Get a health check ID
    health_check_id = sample_services[0].health_checks[0].health_check_id

    with QueryCounter(test_db_session) as counter:
        health_check = OptimizedServiceQueries.get_health_check_with_service(
            test_db_session, health_check_id
        )

        # Access parent service - should be already loaded
        _ = health_check.service  # No additional query

    # Should be exactly 1 query with JOIN
    assert counter.count == 1, f"Expected 1 query with joinedload, got {counter.count}"


@pytest.mark.unit()
@pytest.mark.unit_performance()
def test_query_count_independent_of_result_size(test_db_session):
    """
    Test that query count is independent of result size with eager loading.

    This is the key benefit of eager loading: query count stays constant
    regardless of how many results are returned.
    """
    # Create services with varying numbers of health checks
    for i in range(20):
        service = ServiceRegistry(
            service_id=uuid4(),
            service_name=f"large-service-{i}",
            service_version="1.0.0",
            service_type="api",
            environment="test",
            base_url=f"http://service-{i}:8000",
            health_check_url=f"http://service-{i}:8000/health",
        )
        test_db_session.add(service)

        # Each service has 5 health checks
        for j in range(5):
            health_check = ServiceHealthCheck(
                health_check_id=uuid4(),
                service_id=service.service_id,
                status="HEALTHY",
                response_time_ms=100.0,
                check_type="HTTP",
            )
            test_db_session.add(health_check)

    test_db_session.commit()

    # Test with 5 results
    with QueryCounter(test_db_session) as counter_5:
        services_5 = OptimizedServiceQueries.list_services_with_health_checks(
            test_db_session, limit=5
        )
        for service in services_5:
            _ = service.health_checks

    # Test with 20 results
    with QueryCounter(test_db_session) as counter_20:
        services_20 = OptimizedServiceQueries.list_services_with_health_checks(
            test_db_session, limit=20
        )
        for service in services_20:
            _ = service.health_checks

    # Query count should be the same regardless of result size
    assert counter_5.count == counter_20.count == 2, (
        f"Query count should be constant (2), got {counter_5.count} for 5 results "
        f"and {counter_20.count} for 20 results"
    )


@pytest.mark.unit()
@pytest.mark.unit_performance()
def test_performance_improvement_metrics(test_db_session, sample_services):
    """
    Test and document the performance improvement from eager loading.

    This test measures the reduction in query count and can be used
    to track performance improvements over time.
    """
    from sqlalchemy import select

    # Measure lazy loading (N+1 problem)
    with QueryCounter(test_db_session) as lazy_counter:
        services = (
            test_db_session.execute(select(ServiceRegistry).limit(5)).scalars().all()
        )
        for service in services:
            _ = service.health_checks
            _ = service.metrics

    # Measure eager loading
    with QueryCounter(test_db_session) as eager_counter:
        services = OptimizedServiceQueries.list_services_with_all_relationships(
            test_db_session, limit=5
        )
        for service in services:
            _ = service.health_checks
            _ = service.metrics

    # Calculate improvement
    queries_saved = lazy_counter.count - eager_counter.count
    improvement_percent = (queries_saved / lazy_counter.count) * 100

    # Should save at least 50% of queries
    assert (
        improvement_percent >= 50
    ), f"Expected at least 50% query reduction, got {improvement_percent:.1f}%"

    # Document the improvement
    print("\n=== Performance Improvement ===")
    print(f"Lazy loading: {lazy_counter.count} queries")
    print(f"Eager loading: {eager_counter.count} queries")
    print(f"Queries saved: {queries_saved}")
    print(f"Improvement: {improvement_percent:.1f}%")


@pytest.mark.integration()
@pytest.mark.integration_database()
def test_eager_loading_with_filters(test_db_session, sample_services):
    """
    Test that eager loading works correctly with query filters.

    Eager loading should work seamlessly with WHERE clauses, ORDER BY, etc.
    """
    with QueryCounter(test_db_session) as counter:
        # Query with filter
        health_checks = OptimizedServiceQueries.list_health_checks_with_services(
            test_db_session, limit=10, service_filter=sample_services[0].service_name
        )

        # Access parent services - should be loaded
        for hc in health_checks:
            _ = hc.service

    # Should still be just 1 query with JOIN
    assert (
        counter.count == 1
    ), f"Expected 1 query with joinedload and filter, got {counter.count}"


if __name__ == "__main__":
    """Run tests with pytest"""
    pytest.main([__file__, "-v", "--tb=short"])
