#!/usr/bin/env python3
"""
PAKE System - Optimized Database Queries with Eager Loading
Phase 5: Performance Under Pressure - N+1 Query Elimination

This module provides optimized query methods that use SQLAlchemy's eager loading
to eliminate N+1 queries. It implements:
- joinedload() for many-to-one relationships
- selectinload() for one-to-many relationships

N+1 Query Problem:
The N+1 query problem occurs when:
1. You query for N parent objects
2. For each parent, you query for related child objects
Result: 1 query + N queries = N+1 queries

Solution:
Use eager loading to fetch all data in 1-2 queries instead of N+1.
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

# Import models
from src.services.base.models import (
    ServiceRegistry,
    ServiceHealthCheck,
    ServiceMetrics,
    APIGatewayRoute,
    SystemAlert,
)

logger = logging.getLogger(__name__)


class OptimizedServiceQueries:
    """
    Optimized query methods for ServiceRegistry with eager loading.

    These methods demonstrate proper use of eager loading to eliminate N+1 queries.
    """

    @staticmethod
    def get_service_with_health_checks(
        session: Session, service_id: UUID
    ) -> Optional[ServiceRegistry]:
        """
        Get a service with all its health checks in a single query.

        Without eager loading (N+1 problem):
        - 1 query to fetch service
        - N queries to fetch health checks (one per service.health_checks access)

        With joinedload (optimized):
        - 1 query using LEFT OUTER JOIN to fetch service + health checks

        Args:
            session: Database session
            service_id: Service UUID

        Returns:
            ServiceRegistry with health_checks loaded, or None if not found
        """
        query = (
            select(ServiceRegistry)
            .where(ServiceRegistry.service_id == service_id)
            .options(joinedload(ServiceRegistry.health_checks))
        )

        result = session.execute(query)
        service = result.scalar_one_or_none()

        if service:
            logger.debug(
                f"Loaded service {service.service_name} with "
                f"{len(service.health_checks)} health checks in 1 query"
            )

        return service

    @staticmethod
    def get_service_with_metrics(
        session: Session, service_id: UUID
    ) -> Optional[ServiceRegistry]:
        """
        Get a service with all its metrics in a single query.

        Uses joinedload() for optimal performance with many-to-one relationship.

        Args:
            session: Database session
            service_id: Service UUID

        Returns:
            ServiceRegistry with metrics loaded, or None if not found
        """
        query = (
            select(ServiceRegistry)
            .where(ServiceRegistry.service_id == service_id)
            .options(joinedload(ServiceRegistry.metrics))
        )

        result = session.execute(query)
        service = result.scalar_one_or_none()

        if service:
            logger.debug(
                f"Loaded service {service.service_name} with "
                f"{len(service.metrics)} metrics in 1 query"
            )

        return service

    @staticmethod
    def get_service_with_all_relationships(
        session: Session, service_id: UUID
    ) -> Optional[ServiceRegistry]:
        """
        Get a service with all its relationships in optimized queries.

        Without eager loading (N+1 problem):
        - 1 query to fetch service
        - N queries for health_checks
        - M queries for metrics
        Total: 1 + N + M queries

        With selectinload (optimized):
        - 1 query to fetch service
        - 1 query to fetch all health_checks using WHERE IN
        - 1 query to fetch all metrics using WHERE IN
        Total: 3 queries (regardless of N and M)

        Args:
            session: Database session
            service_id: Service UUID

        Returns:
            ServiceRegistry with all relationships loaded, or None if not found
        """
        query = (
            select(ServiceRegistry)
            .where(ServiceRegistry.service_id == service_id)
            .options(
                selectinload(ServiceRegistry.health_checks),
                selectinload(ServiceRegistry.metrics),
            )
        )

        result = session.execute(query)
        service = result.scalar_one_or_none()

        if service:
            logger.debug(
                f"Loaded service {service.service_name} with all relationships: "
                f"{len(service.health_checks)} health checks, "
                f"{len(service.metrics)} metrics in 3 queries total"
            )

        return service

    @staticmethod
    def list_services_with_health_checks(
        session: Session, limit: int = 100, offset: int = 0
    ) -> List[ServiceRegistry]:
        """
        List services with their health checks using optimized loading.

        Without eager loading (N+1 problem):
        - 1 query to fetch N services
        - N queries to fetch health checks for each service
        Total: 1 + N queries

        With selectinload (optimized):
        - 1 query to fetch N services
        - 1 query to fetch all health checks using WHERE service_id IN (...)
        Total: 2 queries

        Args:
            session: Database session
            limit: Maximum number of services to return
            offset: Number of services to skip

        Returns:
            List of ServiceRegistry objects with health_checks loaded
        """
        query = (
            select(ServiceRegistry)
            .options(selectinload(ServiceRegistry.health_checks))
            .limit(limit)
            .offset(offset)
        )

        result = session.execute(query)
        services = result.scalars().all()

        logger.debug(
            f"Loaded {len(services)} services with health checks in 2 queries "
            f"(instead of {len(services) + 1} with N+1 problem)"
        )

        return list(services)

    @staticmethod
    def list_services_with_all_relationships(
        session: Session, limit: int = 100, offset: int = 0
    ) -> List[ServiceRegistry]:
        """
        List services with all relationships using optimized loading.

        Without eager loading (N+1 problem):
        - 1 query to fetch N services
        - N queries for health_checks
        - N queries for metrics
        Total: 1 + 2N queries

        With selectinload (optimized):
        - 1 query to fetch N services
        - 1 query to fetch all health_checks using WHERE IN
        - 1 query to fetch all metrics using WHERE IN
        Total: 3 queries

        Args:
            session: Database session
            limit: Maximum number of services to return
            offset: Number of services to skip

        Returns:
            List of ServiceRegistry objects with all relationships loaded
        """
        query = (
            select(ServiceRegistry)
            .options(
                selectinload(ServiceRegistry.health_checks),
                selectinload(ServiceRegistry.metrics),
            )
            .limit(limit)
            .offset(offset)
        )

        result = session.execute(query)
        services = result.scalars().all()

        total_health_checks = sum(len(s.health_checks) for s in services)
        total_metrics = sum(len(s.metrics) for s in services)

        logger.debug(
            f"Loaded {len(services)} services with all relationships in 3 queries: "
            f"{total_health_checks} health checks, {total_metrics} metrics "
            f"(instead of {1 + 2 * len(services)} with N+1 problem)"
        )

        return list(services)

    @staticmethod
    def get_health_check_with_service(
        session: Session, health_check_id: UUID
    ) -> Optional[ServiceHealthCheck]:
        """
        Get a health check with its parent service using joinedload.

        For many-to-one relationships, use joinedload() which generates
        a LEFT OUTER JOIN to fetch both objects in a single query.

        Without eager loading:
        - 1 query to fetch health check
        - 1 query to fetch service when accessed
        Total: 2 queries

        With joinedload:
        - 1 query using LEFT OUTER JOIN
        Total: 1 query

        Args:
            session: Database session
            health_check_id: Health check UUID

        Returns:
            ServiceHealthCheck with service loaded, or None if not found
        """
        query = (
            select(ServiceHealthCheck)
            .where(ServiceHealthCheck.health_check_id == health_check_id)
            .options(joinedload(ServiceHealthCheck.service))
        )

        result = session.execute(query)
        health_check = result.scalar_one_or_none()

        if health_check:
            logger.debug(
                f"Loaded health check with service {health_check.service.service_name} "
                f"in 1 query (50% reduction from 2 queries)"
            )

        return health_check

    @staticmethod
    def get_metric_with_service(
        session: Session, metric_id: UUID
    ) -> Optional[ServiceMetrics]:
        """
        Get a metric with its parent service using joinedload.

        Args:
            session: Database session
            metric_id: Metric UUID

        Returns:
            ServiceMetrics with service loaded, or None if not found
        """
        query = (
            select(ServiceMetrics)
            .where(ServiceMetrics.metric_id == metric_id)
            .options(joinedload(ServiceMetrics.service))
        )

        result = session.execute(query)
        metric = result.scalar_one_or_none()

        if metric:
            logger.debug(
                f"Loaded metric with service {metric.service.service_name} "
                f"in 1 query (50% reduction from 2 queries)"
            )

        return metric

    @staticmethod
    def list_health_checks_with_services(
        session: Session,
        limit: int = 100,
        offset: int = 0,
        service_filter: Optional[str] = None,
    ) -> List[ServiceHealthCheck]:
        """
        List health checks with their parent services using optimized loading.

        For many-to-one relationships with multiple child objects,
        joinedload() is more efficient than selectinload() because it uses
        a single query with JOIN instead of two separate queries.

        Without eager loading (N+1):
        - 1 query to fetch N health checks
        - N queries to fetch services
        Total: N + 1 queries

        With joinedload (optimized):
        - 1 query with LEFT OUTER JOIN
        Total: 1 query

        Args:
            session: Database session
            limit: Maximum number of health checks to return
            offset: Number of health checks to skip
            service_filter: Optional service name filter

        Returns:
            List of ServiceHealthCheck objects with service loaded
        """
        query = select(ServiceHealthCheck).options(
            joinedload(ServiceHealthCheck.service)
        )

        if service_filter:
            query = query.join(ServiceHealthCheck.service).where(
                ServiceRegistry.service_name == service_filter
            )

        query = query.limit(limit).offset(offset)

        result = session.execute(query)
        health_checks = result.scalars().unique().all()

        logger.debug(
            f"Loaded {len(health_checks)} health checks with services in 1 query "
            f"(instead of {len(health_checks) + 1} with N+1 problem)"
        )

        return list(health_checks)


# Performance comparison example
def demonstrate_n1_vs_eager_loading():
    """
    Demonstration function showing the difference between N+1 and eager loading.

    This is for educational purposes and testing.
    """
    import time

    from src.services.base.database import get_session

    with get_session() as session:
        # BAD: N+1 query problem
        print("=== N+1 Query Problem (BAD) ===")
        start = time.time()

        # 1 query to fetch services
        services_lazy = session.execute(select(ServiceRegistry).limit(10)).scalars().all()

        # N queries to fetch health checks (one per service when accessed)
        for service in services_lazy:
            health_checks = service.health_checks  # Triggers a new query each time!
            print(f"Service {service.service_name}: {len(health_checks)} health checks")

        n1_time = time.time() - start
        print(f"N+1 approach took {n1_time:.4f} seconds\n")

        # GOOD: Eager loading
        print("=== Eager Loading (GOOD) ===")
        start = time.time()

        # 2 queries total: 1 for services, 1 for all health checks
        services_eager = OptimizedServiceQueries.list_services_with_health_checks(
            session, limit=10
        )

        # No additional queries - data is already loaded!
        for service in services_eager:
            health_checks = service.health_checks  # No query! Data already loaded.
            print(f"Service {service.service_name}: {len(health_checks)} health checks")

        eager_time = time.time() - start
        print(f"Eager loading took {eager_time:.4f} seconds\n")

        improvement = ((n1_time - eager_time) / n1_time) * 100
        print(f"Performance improvement: {improvement:.1f}% faster")
        print(f"Queries reduced: {len(services_lazy) + 1} -> 2")
