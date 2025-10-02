"""
Database Performance Profiling and Optimization
===============================================

This module provides comprehensive database performance profiling,
N+1 query detection, and optimization recommendations for the PAKE System.

Key Features:
- SQL query logging and analysis
- N+1 query detection and elimination
- Query performance profiling
- Database optimization recommendations
- Automated performance monitoring
"""

import logging
import time
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from pathlib import Path
from datetime import datetime, timedelta
import sqlalchemy
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import Pool
import psycopg2
from psycopg2.extensions import connection as PgConnection


@dataclass
class QueryMetrics:
    """Database query metrics"""
    query_id: str
    query_text: str
    execution_time_ms: float
    timestamp: str
    connection_id: str
    parameters: Dict[str, Any]
    result_count: int
    query_type: str  # SELECT, INSERT, UPDATE, DELETE
    table_name: Optional[str] = None
    is_n_plus_one: bool = False
    optimization_suggestions: List[str] = None


@dataclass
class NPlusOnePattern:
    """N+1 query pattern detection"""
    pattern_id: str
    parent_query: str
    child_queries: List[str]
    frequency: int
    total_execution_time_ms: float
    optimization_strategy: str
    suggested_fix: str


class DatabaseProfiler:
    """Comprehensive database performance profiler"""

    def __init__(self, log_file: str = "logs/database_profiling.log"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.logger = logging.getLogger("database_profiler")
        self.logger.setLevel(logging.INFO)

        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Query tracking
        self.query_metrics: List[QueryMetrics] = []
        self.n_plus_one_patterns: List[NPlusOnePattern] = []
        self.query_counter = Counter()
        self.execution_times: Dict[str, List[float]] = defaultdict(list)

        # Performance thresholds
        self.slow_query_threshold_ms = 1000.0  # 1 second
        self.n_plus_one_threshold = 5  # Minimum queries to consider N+1

    def enable_profiling(self, engine: Engine):
        """Enable database profiling for SQLAlchemy engine"""

        @event.listens_for(engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Called before cursor execution"""
            context._query_start_time = time.time()
            context._query_statement = statement
            context._query_parameters = parameters

        @event.listens_for(engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Called after cursor execution"""
            if hasattr(context, '_query_start_time'):
                execution_time = (time.time() - context._query_start_time) * 1000

                # Extract query information
                query_type = self._extract_query_type(statement)
                table_name = self._extract_table_name(statement)

                # Create query metrics
                query_id = f"{hash(statement)}_{int(time.time() * 1000)}"
                metrics = QueryMetrics(
                    query_id=query_id,
                    query_text=statement,
                    execution_time_ms=execution_time,
                    timestamp=datetime.now().isoformat(),
                    connection_id=str(id(conn)),
                    parameters=parameters or {},
                    result_count=cursor.rowcount if hasattr(cursor, 'rowcount') else 0,
                    query_type=query_type,
                    table_name=table_name
                )

                # Store metrics
                self.query_metrics.append(metrics)
                self.query_counter[statement] += 1
                self.execution_times[statement].append(execution_time)

                # Log slow queries
                if execution_time > self.slow_query_threshold_ms:
                    self.logger.warning(
                        f"Slow query detected: {execution_time:.2f}ms - {statement[:100]}..."
                    )

                # Detect N+1 patterns
                self._detect_n_plus_one_patterns(metrics)

    def _extract_query_type(self, statement: str) -> str:
        """Extract query type from SQL statement"""
        statement_upper = statement.strip().upper()
        if statement_upper.startswith('SELECT'):
            return 'SELECT'
        elif statement_upper.startswith('INSERT'):
            return 'INSERT'
        elif statement_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif statement_upper.startswith('DELETE'):
            return 'DELETE'
        else:
            return 'OTHER'

    def _extract_table_name(self, statement: str) -> Optional[str]:
        """Extract table name from SQL statement"""
        # Simple regex patterns for common SQL statements
        patterns = [
            r'FROM\s+(\w+)',
            r'INTO\s+(\w+)',
            r'UPDATE\s+(\w+)',
            r'DELETE\s+FROM\s+(\w+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, statement, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _detect_n_plus_one_patterns(self, metrics: QueryMetrics):
        """Detect N+1 query patterns"""
        if metrics.query_type != 'SELECT':
            return

        # Look for patterns in recent queries
        recent_queries = [q for q in self.query_metrics[-100:] if q.query_type == 'SELECT']

        # Group queries by table and pattern
        table_queries = defaultdict(list)
        for query in recent_queries:
            if query.table_name:
                table_queries[query.table_name].append(query)

        # Detect N+1 patterns
        for table, queries in table_queries.items():
            if len(queries) >= self.n_plus_one_threshold:
                # Check if queries are similar (same structure, different parameters)
                query_patterns = defaultdict(list)
                for query in queries:
                    # Normalize query by removing parameter values
                    normalized = self._normalize_query(query.query_text)
                    query_patterns[normalized].append(query)

                # Find patterns with multiple similar queries
                for pattern, pattern_queries in query_patterns.items():
                    if len(pattern_queries) >= self.n_plus_one_threshold:
                        self._create_n_plus_one_pattern(pattern, pattern_queries)

    def _normalize_query(self, query: str) -> str:
        """Normalize query by removing parameter values"""
        # Remove parameter placeholders and values
        normalized = re.sub(r'\$\d+', '$?', query)
        normalized = re.sub(r'%s', '?', normalized)
        normalized = re.sub(r':\w+', ':?', normalized)
        return normalized.strip()

    def _create_n_plus_one_pattern(self, pattern: str, queries: List[QueryMetrics]):
        """Create N+1 pattern record"""
        pattern_id = f"n_plus_one_{hash(pattern)}_{int(time.time())}"

        # Calculate total execution time
        total_time = sum(q.execution_time_ms for q in queries)

        # Determine optimization strategy
        optimization_strategy = self._determine_optimization_strategy(pattern, queries)
        suggested_fix = self._generate_optimization_suggestion(pattern, queries)

        n_plus_one_pattern = NPlusOnePattern(
            pattern_id=pattern_id,
            parent_query=pattern,
            child_queries=[q.query_text for q in queries],
            frequency=len(queries),
            total_execution_time_ms=total_time,
            optimization_strategy=optimization_strategy,
            suggested_fix=suggested_fix
        )

        self.n_plus_one_patterns.append(n_plus_one_pattern)

        self.logger.warning(
            f"N+1 pattern detected: {len(queries)} queries, "
            f"{total_time:.2f}ms total time - {pattern[:100]}..."
        )

    def _determine_optimization_strategy(self, pattern: str, queries: List[QueryMetrics]) -> str:
        """Determine optimization strategy for N+1 pattern"""
        if 'JOIN' in pattern.upper():
            return "query_optimization"
        elif 'WHERE' in pattern.upper() and 'IN' in pattern.upper():
            return "batch_loading"
        elif 'ORDER BY' in pattern.upper():
            return "index_optimization"
        else:
            return "eager_loading"

    def _generate_optimization_suggestion(self, pattern: str, queries: List[QueryMetrics]) -> str:
        """Generate optimization suggestion for N+1 pattern"""
        table_name = self._extract_table_name(pattern)

        if 'WHERE' in pattern.upper():
            return f"Use eager loading with joinedload() or selectinload() for {table_name} relationships"
        elif 'JOIN' in pattern.upper():
            return f"Optimize JOIN query for {table_name} - consider adding indexes or restructuring query"
        else:
            return f"Implement batch loading for {table_name} to reduce query count"

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.query_metrics:
            return {"message": "No queries recorded"}

        # Calculate statistics
        total_queries = len(self.query_metrics)
        total_execution_time = sum(q.execution_time_ms for q in self.query_metrics)
        avg_execution_time = total_execution_time / total_queries

        # Slow queries
        slow_queries = [q for q in self.query_metrics if q.execution_time_ms > self.slow_query_threshold_ms]

        # Query type distribution
        query_types = Counter(q.query_type for q in self.query_metrics)

        # Table usage
        table_usage = Counter(q.table_name for q in self.query_metrics if q.table_name)

        # N+1 patterns
        n_plus_one_count = len(self.n_plus_one_patterns)
        n_plus_one_time = sum(p.total_execution_time_ms for p in self.n_plus_one_patterns)

        return {
            "summary": {
                "total_queries": total_queries,
                "total_execution_time_ms": total_execution_time,
                "avg_execution_time_ms": avg_execution_time,
                "slow_queries_count": len(slow_queries),
                "n_plus_one_patterns_count": n_plus_one_count,
                "n_plus_one_time_ms": n_plus_one_time
            },
            "query_types": dict(query_types),
            "table_usage": dict(table_usage.most_common(10)),
            "slow_queries": [
                {
                    "query": q.query_text[:100] + "..." if len(q.query_text) > 100 else q.query_text,
                    "execution_time_ms": q.execution_time_ms,
                    "table": q.table_name
                }
                for q in slow_queries[:10]
            ],
            "n_plus_one_patterns": [
                {
                    "pattern": p.parent_query[:100] + "..." if len(p.parent_query) > 100 else p.parent_query,
                    "frequency": p.frequency,
                    "total_time_ms": p.total_execution_time_ms,
                    "strategy": p.optimization_strategy,
                    "suggestion": p.suggested_fix
                }
                for p in self.n_plus_one_patterns[:5]
            ]
        }

    def generate_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        summary = self.get_performance_summary()

        recommendations = []

        # N+1 query recommendations
        if summary["summary"]["n_plus_one_patterns_count"] > 0:
            recommendations.append({
                "priority": "high",
                "category": "N+1 Queries",
                "description": f"Found {summary['summary']['n_plus_one_patterns_count']} N+1 patterns",
                "impact": f"Total time: {summary['summary']['n_plus_one_time_ms']:.2f}ms",
                "suggestions": [
                    "Use SQLAlchemy's joinedload() for many-to-one relationships",
                    "Use selectinload() for one-to-many relationships",
                    "Implement batch loading for bulk operations",
                    "Consider using subqueryload() for complex relationships"
                ]
            })

        # Slow query recommendations
        if summary["summary"]["slow_queries_count"] > 0:
            recommendations.append({
                "priority": "medium",
                "category": "Slow Queries",
                "description": f"Found {summary['summary']['slow_queries_count']} slow queries",
                "impact": "Performance degradation",
                "suggestions": [
                    "Add database indexes on frequently queried columns",
                    "Optimize query structure and joins",
                    "Consider query result caching",
                    "Implement query result pagination"
                ]
            })

        # General recommendations
        if summary["summary"]["avg_execution_time_ms"] > 100:
            recommendations.append({
                "priority": "low",
                "category": "General Performance",
                "description": "Average query execution time is high",
                "impact": "Overall system performance",
                "suggestions": [
                    "Review database connection pooling settings",
                    "Consider read replicas for read-heavy workloads",
                    "Implement query result caching",
                    "Monitor database resource usage"
                ]
            })

        return {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_queries_analyzed": summary["summary"]["total_queries"],
                "analysis_period": "current_session"
            },
            "performance_summary": summary,
            "recommendations": recommendations,
            "optimization_priority": self._calculate_optimization_priority(recommendations)
        }

    def _calculate_optimization_priority(self, recommendations: List[Dict]) -> str:
        """Calculate overall optimization priority"""
        if not recommendations:
            return "low"

        priorities = [r["priority"] for r in recommendations]
        if "high" in priorities:
            return "high"
        elif "medium" in priorities:
            return "medium"
        else:
            return "low"

    def save_report(self, filename: str = None) -> Path:
        """Save optimization report to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"database_optimization_report_{timestamp}.json"

        report = self.generate_optimization_report()

        report_file = Path("performance_tests/results") / filename
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Database optimization report saved to: {report_file}")
        return report_file


class SQLAlchemyOptimizer:
    """SQLAlchemy-specific optimization utilities"""

    @staticmethod
    def optimize_relationships(session: Session, model_class, relationship_name: str):
        """Optimize relationship loading using eager loading"""
        from sqlalchemy.orm import joinedload, selectinload

        # Determine optimal loading strategy based on relationship type
        relationship = getattr(model_class, relationship_name)

        if relationship.property.direction.name == 'MANYTOONE':
            # Use joinedload for many-to-one relationships
            return session.query(model_class).options(joinedload(relationship_name))
        else:
            # Use selectinload for one-to-many relationships
            return session.query(model_class).options(selectinload(relationship_name))

    @staticmethod
    def batch_load_relationships(session: Session, model_class, relationship_name: str, ids: List[int]):
        """Batch load relationships for multiple objects"""
        from sqlalchemy.orm import selectinload

        return session.query(model_class).filter(
            model_class.id.in_(ids)
        ).options(selectinload(relationship_name)).all()

    @staticmethod
    def optimize_query_with_indexes(query, table_name: str, columns: List[str]):
        """Add query hints for index usage"""
        # This would be database-specific implementation
        # For PostgreSQL, you could use query hints
        return query.with_hint(table_name, f"INDEX({', '.join(columns)})")


def main():
    """Main function for database profiling"""
    import argparse

    parser = argparse.ArgumentParser(description="PAKE System Database Profiler")
    parser.add_argument("--enable-profiling", action="store_true",
                       help="Enable database profiling")
    parser.add_argument("--generate-report", action="store_true",
                       help="Generate optimization report")
    parser.add_argument("--log-file", default="logs/database_profiling.log",
                       help="Log file path")

    args = parser.parse_args()

    # Initialize profiler
    profiler = DatabaseProfiler(args.log_file)

    if args.enable_profiling:
        print("Database profiling enabled. Run your application to collect metrics.")
        print(f"Logs will be written to: {args.log_file}")

    if args.generate_report:
        report_file = profiler.save_report()
        print(f"Optimization report generated: {report_file}")

        # Print summary
        summary = profiler.get_performance_summary()
        print("\n" + "="*60)
        print("DATABASE PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Total Queries: {summary['summary']['total_queries']}")
        print(f"Avg Execution Time: {summary['summary']['avg_execution_time_ms']:.2f}ms")
        print(f"Slow Queries: {summary['summary']['slow_queries_count']}")
        print(f"N+1 Patterns: {summary['summary']['n_plus_one_patterns_count']}")

        if summary['n_plus_one_patterns']:
            print("\nN+1 Patterns Detected:")
            for pattern in summary['n_plus_one_patterns']:
                print(f"  - {pattern['pattern']}")
                print(f"    Frequency: {pattern['frequency']}, Time: {pattern['total_time_ms']:.2f}ms")
                print(f"    Suggestion: {pattern['suggestion']}")


if __name__ == "__main__":
    main()
