#!/usr/bin/env python3
"""
PAKE System - Comprehensive Test Coverage Reporting and Monitoring

Generates detailed test coverage reports, monitors coverage trends,
and provides actionable insights for maintaining high code quality.

Features:
- Multi-level coverage reporting (unit, integration, e2e)
- Coverage trend analysis
- Coverage gap identification
- Automated coverage monitoring
- Quality gate enforcement
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import coverage
import pytest
from coverage.results import Numbers
from coverage.report import get_analysis_to_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CoverageLevel(Enum):
    """Coverage level definitions"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    COMBINED = "combined"


@dataclass
class CoverageMetrics:
    """Coverage metrics data structure"""
    level: CoverageLevel
    lines_covered: int
    lines_total: int
    line_percentage: float
    branches_covered: int
    branches_total: int
    branch_percentage: float
    functions_covered: int
    functions_total: int
    function_percentage: float
    timestamp: datetime
    test_count: int
    execution_time: float


@dataclass
class CoverageTrend:
    """Coverage trend analysis"""
    level: CoverageLevel
    current_coverage: float
    previous_coverage: float
    trend_direction: str  # "up", "down", "stable"
    trend_percentage: float
    days_since_last_run: int


@dataclass
class CoverageGap:
    """Coverage gap identification"""
    file_path: str
    function_name: str
    line_number: int
    gap_type: str  # "uncovered", "partial", "missing_test"
    priority: str  # "high", "medium", "low"
    recommendation: str


class CoverageReporter:
    """Comprehensive test coverage reporting and monitoring"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.coverage_dir = project_root / "coverage"
        self.reports_dir = project_root / "coverage_reports"
        self.trends_dir = project_root / "coverage_trends"
        
        # Create directories
        self.coverage_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        self.trends_dir.mkdir(exist_ok=True)
        
        # Coverage thresholds
        self.thresholds = {
            CoverageLevel.UNIT: 85.0,
            CoverageLevel.INTEGRATION: 80.0,
            CoverageLevel.E2E: 75.0,
            CoverageLevel.COMBINED: 85.0
        }
        
        logger.info(f"CoverageReporter initialized for project: {project_root}")

    async def generate_coverage_report(self, level: CoverageLevel) -> CoverageMetrics:
        """Generate coverage report for specific test level"""
        logger.info(f"Generating coverage report for {level.value} tests")
        
        # Run tests with coverage
        test_dir = self.project_root / "tests" / level.value
        if not test_dir.exists():
            logger.warning(f"Test directory not found: {test_dir}")
            return None
        
        # Configure coverage
        cov = coverage.Coverage(
            source=[str(self.project_root / "src")],
            omit=[
                "*/tests/*",
                "*/test_*",
                "*/__pycache__/*",
                "*/venv/*",
                "*/.venv/*",
                "*/mcp-env/*",
                "*/test_env/*"
            ]
        )
        
        # Start coverage
        cov.start()
        
        # Run tests
        start_time = datetime.now(timezone.utc)
        
        pytest_args = [
            str(test_dir),
            "--cov=src",
            "--cov-report=xml",
            "--cov-report=html",
            "--cov-report=json",
            "--junitxml=test-results.xml",
            "-v"
        ]
        
        # Add level-specific markers
        if level == CoverageLevel.UNIT:
            pytest_args.extend(["-m", "unit"])
        elif level == CoverageLevel.INTEGRATION:
            pytest_args.extend(["-m", "integration"])
        elif level == CoverageLevel.E2E:
            pytest_args.extend(["-m", "e2e"])
        
        exit_code = pytest.main(pytest_args)
        end_time = datetime.now(timezone.utc)
        
        # Stop coverage
        cov.stop()
        cov.save()
        
        # Generate coverage report
        cov.report()
        
        # Get coverage data
        total = cov.total
        if total is None:
            logger.error("No coverage data collected")
            return None
        
        # Calculate metrics
        metrics = CoverageMetrics(
            level=level,
            lines_covered=total.ncovered_lines,
            lines_total=total.nlines,
            line_percentage=total.percent_covered,
            branches_covered=total.ncovered_branches,
            branches_total=total.nbranches,
            branch_percentage=total.percent_covered_display,
            functions_covered=total.ncovered_functions,
            functions_total=total.nfunctions,
            function_percentage=total.percent_covered_display,
            timestamp=datetime.now(timezone.utc),
            test_count=self._count_tests(test_dir),
            execution_time=(end_time - start_time).total_seconds()
        )
        
        # Save metrics
        await self._save_coverage_metrics(metrics)
        
        logger.info(f"Coverage report generated for {level.value}: {metrics.line_percentage:.2f}%")
        return metrics

    async def generate_combined_coverage_report(self) -> CoverageMetrics:
        """Generate combined coverage report from all test levels"""
        logger.info("Generating combined coverage report")
        
        # Load individual coverage reports
        unit_metrics = await self._load_coverage_metrics(CoverageLevel.UNIT)
        integration_metrics = await self._load_coverage_metrics(CoverageLevel.INTEGRATION)
        e2e_metrics = await self._load_coverage_metrics(CoverageLevel.E2E)
        
        if not all([unit_metrics, integration_metrics, e2e_metrics]):
            logger.error("Missing coverage metrics for combined report")
            return None
        
        # Calculate combined metrics (weighted average)
        total_lines_covered = (
            unit_metrics.lines_covered * 0.7 +  # Unit tests weight: 70%
            integration_metrics.lines_covered * 0.2 +  # Integration tests weight: 20%
            e2e_metrics.lines_covered * 0.1  # E2E tests weight: 10%
        )
        
        total_lines = (
            unit_metrics.lines_total * 0.7 +
            integration_metrics.lines_total * 0.2 +
            e2e_metrics.lines_total * 0.1
        )
        
        combined_percentage = (total_lines_covered / total_lines * 100) if total_lines > 0 else 0
        
        combined_metrics = CoverageMetrics(
            level=CoverageLevel.COMBINED,
            lines_covered=int(total_lines_covered),
            lines_total=int(total_lines),
            line_percentage=combined_percentage,
            branches_covered=int(
                unit_metrics.branches_covered * 0.7 +
                integration_metrics.branches_covered * 0.2 +
                e2e_metrics.branches_covered * 0.1
            ),
            branches_total=int(
                unit_metrics.branches_total * 0.7 +
                integration_metrics.branches_total * 0.2 +
                e2e_metrics.branches_total * 0.1
            ),
            branch_percentage=combined_percentage,
            functions_covered=int(
                unit_metrics.functions_covered * 0.7 +
                integration_metrics.functions_covered * 0.2 +
                e2e_metrics.functions_covered * 0.1
            ),
            functions_total=int(
                unit_metrics.functions_total * 0.7 +
                integration_metrics.functions_total * 0.2 +
                e2e_metrics.functions_total * 0.1
            ),
            function_percentage=combined_percentage,
            timestamp=datetime.now(timezone.utc),
            test_count=unit_metrics.test_count + integration_metrics.test_count + e2e_metrics.test_count,
            execution_time=unit_metrics.execution_time + integration_metrics.execution_time + e2e_metrics.execution_time
        )
        
        # Save combined metrics
        await self._save_coverage_metrics(combined_metrics)
        
        logger.info(f"Combined coverage report generated: {combined_metrics.line_percentage:.2f}%")
        return combined_metrics

    async def analyze_coverage_trends(self) -> List[CoverageTrend]:
        """Analyze coverage trends over time"""
        logger.info("Analyzing coverage trends")
        
        trends = []
        
        for level in [CoverageLevel.UNIT, CoverageLevel.INTEGRATION, CoverageLevel.E2E, CoverageLevel.COMBINED]:
            current_metrics = await self._load_coverage_metrics(level)
            if not current_metrics:
                continue
            
            # Load historical data
            historical_data = await self._load_historical_coverage(level)
            if not historical_data:
                continue
            
            # Find most recent previous run
            previous_metrics = max(historical_data, key=lambda x: x.timestamp)
            
            # Calculate trend
            trend_direction = "stable"
            if current_metrics.line_percentage > previous_metrics.line_percentage + 0.1:
                trend_direction = "up"
            elif current_metrics.line_percentage < previous_metrics.line_percentage - 0.1:
                trend_direction = "down"
            
            trend_percentage = current_metrics.line_percentage - previous_metrics.line_percentage
            days_since_last_run = (current_metrics.timestamp - previous_metrics.timestamp).days
            
            trend = CoverageTrend(
                level=level,
                current_coverage=current_metrics.line_percentage,
                previous_coverage=previous_metrics.line_percentage,
                trend_direction=trend_direction,
                trend_percentage=trend_percentage,
                days_since_last_run=days_since_last_run
            )
            
            trends.append(trend)
        
        logger.info(f"Coverage trends analyzed: {len(trends)} trends found")
        return trends

    async def identify_coverage_gaps(self) -> List[CoverageGap]:
        """Identify coverage gaps and provide recommendations"""
        logger.info("Identifying coverage gaps")
        
        gaps = []
        
        # Load coverage data
        cov = coverage.Coverage()
        cov.load()
        
        # Analyze each file
        for file_path in cov.get_data().measured_files():
            if not file_path.startswith(str(self.project_root / "src")):
                continue
            
            # Get file analysis
            analysis = cov.analysis(file_path)
            if not analysis:
                continue
            
            # Find uncovered lines
            uncovered_lines = analysis[2]  # Missing lines
            if uncovered_lines:
                for line_num in uncovered_lines:
                    gap = CoverageGap(
                        file_path=file_path,
                        function_name=self._get_function_name(file_path, line_num),
                        line_number=line_num,
                        gap_type="uncovered",
                        priority=self._assess_gap_priority(file_path, line_num),
                        recommendation=self._generate_recommendation(file_path, line_num)
                    )
                    gaps.append(gap)
        
        # Sort by priority
        gaps.sort(key=lambda x: {"high": 3, "medium": 2, "low": 1}[x.priority], reverse=True)
        
        logger.info(f"Coverage gaps identified: {len(gaps)} gaps found")
        return gaps

    async def generate_coverage_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive coverage dashboard"""
        logger.info("Generating coverage dashboard")
        
        # Get current metrics
        unit_metrics = await self._load_coverage_metrics(CoverageLevel.UNIT)
        integration_metrics = await self._load_coverage_metrics(CoverageLevel.INTEGRATION)
        e2e_metrics = await self._load_coverage_metrics(CoverageLevel.E2E)
        combined_metrics = await self._load_coverage_metrics(CoverageLevel.COMBINED)
        
        # Get trends
        trends = await self._analyze_coverage_trends()
        
        # Get gaps
        gaps = await self._identify_coverage_gaps()
        
        # Generate dashboard
        dashboard = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overview": {
                "unit_coverage": unit_metrics.line_percentage if unit_metrics else 0,
                "integration_coverage": integration_metrics.line_percentage if integration_metrics else 0,
                "e2e_coverage": e2e_metrics.line_percentage if e2e_metrics else 0,
                "combined_coverage": combined_metrics.line_percentage if combined_metrics else 0,
                "total_tests": sum([
                    unit_metrics.test_count if unit_metrics else 0,
                    integration_metrics.test_count if integration_metrics else 0,
                    e2e_metrics.test_count if e2e_metrics else 0
                ])
            },
            "trends": [asdict(trend) for trend in trends],
            "gaps": [asdict(gap) for gap in gaps[:10]],  # Top 10 gaps
            "quality_gates": {
                "unit_tests": {
                    "threshold": self.thresholds[CoverageLevel.UNIT],
                    "current": unit_metrics.line_percentage if unit_metrics else 0,
                    "passed": unit_metrics.line_percentage >= self.thresholds[CoverageLevel.UNIT] if unit_metrics else False
                },
                "integration_tests": {
                    "threshold": self.thresholds[CoverageLevel.INTEGRATION],
                    "current": integration_metrics.line_percentage if integration_metrics else 0,
                    "passed": integration_metrics.line_percentage >= self.thresholds[CoverageLevel.INTEGRATION] if integration_metrics else False
                },
                "e2e_tests": {
                    "threshold": self.thresholds[CoverageLevel.E2E],
                    "current": e2e_metrics.line_percentage if e2e_metrics else 0,
                    "passed": e2e_metrics.line_percentage >= self.thresholds[CoverageLevel.E2E] if e2e_metrics else False
                },
                "combined": {
                    "threshold": self.thresholds[CoverageLevel.COMBINED],
                    "current": combined_metrics.line_percentage if combined_metrics else 0,
                    "passed": combined_metrics.line_percentage >= self.thresholds[CoverageLevel.COMBINED] if combined_metrics else False
                }
            },
            "recommendations": self._generate_recommendations(unit_metrics, integration_metrics, e2e_metrics, combined_metrics, trends, gaps)
        }
        
        # Save dashboard
        dashboard_file = self.reports_dir / "coverage_dashboard.json"
        with open(dashboard_file, 'w') as f:
            json.dump(dashboard, f, indent=2, default=str)
        
        logger.info(f"Coverage dashboard generated: {dashboard_file}")
        return dashboard

    async def enforce_quality_gates(self) -> bool:
        """Enforce quality gates based on coverage thresholds"""
        logger.info("Enforcing quality gates")
        
        all_passed = True
        
        for level in [CoverageLevel.UNIT, CoverageLevel.INTEGRATION, CoverageLevel.E2E, CoverageLevel.COMBINED]:
            metrics = await self._load_coverage_metrics(level)
            if not metrics:
                logger.error(f"No coverage metrics found for {level.value}")
                all_passed = False
                continue
            
            threshold = self.thresholds[level]
            if metrics.line_percentage < threshold:
                logger.error(f"Quality gate failed for {level.value}: {metrics.line_percentage:.2f}% < {threshold}%")
                all_passed = False
            else:
                logger.info(f"Quality gate passed for {level.value}: {metrics.line_percentage:.2f}% >= {threshold}%")
        
        if all_passed:
            logger.info("All quality gates passed")
        else:
            logger.error("Some quality gates failed")
        
        return all_passed

    # Helper methods
    
    def _count_tests(self, test_dir: Path) -> int:
        """Count number of tests in directory"""
        count = 0
        for py_file in test_dir.rglob("test_*.py"):
            with open(py_file, 'r') as f:
                content = f.read()
                count += content.count("def test_")
        return count
    
    async def _save_coverage_metrics(self, metrics: CoverageMetrics):
        """Save coverage metrics to file"""
        metrics_file = self.trends_dir / f"{metrics.level.value}_coverage.json"
        with open(metrics_file, 'w') as f:
            json.dump(asdict(metrics), f, indent=2, default=str)
    
    async def _load_coverage_metrics(self, level: CoverageLevel) -> Optional[CoverageMetrics]:
        """Load coverage metrics from file"""
        metrics_file = self.trends_dir / f"{level.value}_coverage.json"
        if not metrics_file.exists():
            return None
        
        with open(metrics_file, 'r') as f:
            data = json.load(f)
            return CoverageMetrics(**data)
    
    async def _load_historical_coverage(self, level: CoverageLevel) -> List[CoverageMetrics]:
        """Load historical coverage data"""
        # This would typically load from a database or file system
        # For now, return empty list
        return []
    
    def _get_function_name(self, file_path: str, line_num: int) -> str:
        """Get function name for a given line number"""
        # This would parse the file to find the function name
        # For now, return a placeholder
        return "unknown_function"
    
    def _assess_gap_priority(self, file_path: str, line_num: int) -> str:
        """Assess priority of coverage gap"""
        # High priority for critical files
        if "auth" in file_path or "security" in file_path:
            return "high"
        elif "api" in file_path or "service" in file_path:
            return "medium"
        else:
            return "low"
    
    def _generate_recommendation(self, file_path: str, line_num: int) -> str:
        """Generate recommendation for coverage gap"""
        return f"Add unit test for line {line_num} in {file_path}"
    
    def _generate_recommendations(self, unit_metrics, integration_metrics, e2e_metrics, combined_metrics, trends, gaps) -> List[str]:
        """Generate overall recommendations"""
        recommendations = []
        
        if combined_metrics and combined_metrics.line_percentage < self.thresholds[CoverageLevel.COMBINED]:
            recommendations.append(f"Increase overall coverage from {combined_metrics.line_percentage:.2f}% to {self.thresholds[CoverageLevel.COMBINED]}%")
        
        for trend in trends:
            if trend.trend_direction == "down":
                recommendations.append(f"Coverage trend is declining for {trend.level.value} tests")
        
        if len(gaps) > 20:
            recommendations.append(f"Address {len(gaps)} coverage gaps, focusing on high-priority items")
        
        return recommendations


async def main():
    """Main function for coverage reporting"""
    project_root = Path(__file__).parent.parent
    reporter = CoverageReporter(project_root)
    
    # Generate coverage reports
    logger.info("Starting comprehensive coverage reporting")
    
    # Generate individual reports
    unit_metrics = await reporter.generate_coverage_report(CoverageLevel.UNIT)
    integration_metrics = await reporter.generate_coverage_report(CoverageLevel.INTEGRATION)
    e2e_metrics = await reporter.generate_coverage_report(CoverageLevel.E2E)
    
    # Generate combined report
    combined_metrics = await reporter.generate_combined_coverage_report()
    
    # Generate dashboard
    dashboard = await reporter.generate_coverage_dashboard()
    
    # Enforce quality gates
    quality_gates_passed = await reporter.enforce_quality_gates()
    
    # Print summary
    print("\n" + "="*80)
    print("PAKE SYSTEM - COVERAGE REPORT SUMMARY")
    print("="*80)
    
    if unit_metrics:
        print(f"Unit Tests Coverage: {unit_metrics.line_percentage:.2f}% ({unit_metrics.test_count} tests)")
    if integration_metrics:
        print(f"Integration Tests Coverage: {integration_metrics.line_percentage:.2f}% ({integration_metrics.test_count} tests)")
    if e2e_metrics:
        print(f"E2E Tests Coverage: {e2e_metrics.line_percentage:.2f}% ({e2e_metrics.test_count} tests)")
    if combined_metrics:
        print(f"Combined Coverage: {combined_metrics.line_percentage:.2f}%")
    
    print(f"Quality Gates: {'PASSED' if quality_gates_passed else 'FAILED'}")
    print("="*80)
    
    # Exit with appropriate code
    sys.exit(0 if quality_gates_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
