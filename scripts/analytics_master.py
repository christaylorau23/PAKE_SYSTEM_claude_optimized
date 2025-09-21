#!/usr/bin/env python3
"""
Analytics & Optimization Master Controller
Complete analytics, optimization, and A/B testing integration
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

# Import all analytics components
try:
    from ab_testing_framework import ABTestingFramework, ContentABTesting, TestStatus
    from analytics_engine import PerformanceReport, VibeAnalyticsEngine
    from optimization_engine import (
        IntelligentOptimizationEngine,
        OptimizationRecommendation,
    )
except ImportError as e:
    print(f"Analytics modules not available: {e}")
    print("Make sure all analytics modules are in the same directory")


class AnalyticsMasterController:
    """Master controller for analytics, optimization, and experimentation"""

    def __init__(self, config_path: str = None):
        """Initialize the master analytics system"""
        self.logger = self._setup_logging()
        self.config = self._load_configuration(config_path)

        # Initialize all components
        self.analytics_engine = VibeAnalyticsEngine(config_path)
        self.optimization_engine = IntelligentOptimizationEngine()
        self.ab_testing = ABTestingFramework()
        self.content_testing = ContentABTesting()

        # System state
        self.is_running = False
        self.background_tasks = []

        # Performance tracking
        self.performance_history = []
        self.optimization_history = []

        self.logger.info("Analytics Master Controller initialized successfully")

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        log_dir = Path("../logs")
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_dir / "analytics_master.log"),
                logging.StreamHandler(),
            ],
        )

        return logging.getLogger(__name__)

    def _load_configuration(self, config_path: str = None) -> dict:
        """Load master configuration"""
        default_config = {
            "automation": {
                "auto_optimize": True,
                "auto_run_ab_tests": True,
                "daily_reports": True,
                "real_time_alerts": True,
            },
            "optimization": {
                "min_confidence_threshold": 0.8,
                "min_impact_threshold": 10.0,  # 10% improvement
                "run_frequency_hours": 6,
            },
            "ab_testing": {
                "auto_create_tests": True,
                "min_sample_size": 1000,
                "max_concurrent_tests": 5,
                "auto_stop_conclusive_tests": True,
            },
            "reporting": {
                "executive_summary_time": "09:00",
                "detailed_report_time": "18:00",
                "weekly_deep_dive": "monday",
            },
            "thresholds": {
                "critical_performance_drop": 25.0,
                "significant_improvement": 15.0,
                "viral_content_threshold": 100000,
            },
        }

        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    async def start_master_system(self):
        """Start the complete analytics master system"""
        self.logger.info("Starting Analytics Master System...")

        if self.is_running:
            self.logger.warning("System is already running")
            return

        self.is_running = True

        # Start background automation tasks
        if self.config["automation"]["auto_optimize"]:
            optimization_task = asyncio.create_task(self._run_optimization_loop())
            self.background_tasks.append(optimization_task)

        if self.config["automation"]["auto_run_ab_tests"]:
            ab_testing_task = asyncio.create_task(self._run_ab_testing_automation())
            self.background_tasks.append(ab_testing_task)

        if self.config["automation"]["daily_reports"]:
            reporting_task = asyncio.create_task(self._run_reporting_schedule())
            self.background_tasks.append(reporting_task)

        if self.config["automation"]["real_time_alerts"]:
            alerts_task = asyncio.create_task(self._run_real_time_monitoring())
            self.background_tasks.append(alerts_task)

        self.logger.info("Analytics Master System started with all automation enabled")

    async def stop_master_system(self):
        """Stop the analytics master system"""
        self.logger.info("Stopping Analytics Master System...")

        self.is_running = False

        # Cancel all background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        self.background_tasks.clear()

        self.logger.info("Analytics Master System stopped")

    async def run_complete_analysis_cycle(self) -> dict:
        """Run complete analysis and optimization cycle"""
        self.logger.info("Starting complete analysis cycle...")

        cycle_results = {
            "timestamp": datetime.now(),
            "analytics_report": None,
            "optimization_results": None,
            "ab_test_updates": None,
            "recommendations": [],
            "alerts": [],
            "performance_summary": {},
        }

        try:
            # 1. Generate comprehensive analytics report
            self.logger.info("Generating analytics report...")
            analytics_report = await self.analytics_engine.generate_daily_report()
            cycle_results["analytics_report"] = analytics_report

            # 2. Collect current metrics for optimization
            current_metrics = await self.analytics_engine.collect_all_metrics()

            # 3. Run optimization engine
            self.logger.info("Running optimization analysis...")
            optimization_results = (
                await self.optimization_engine.run_optimization_cycle(current_metrics)
            )
            cycle_results["optimization_results"] = optimization_results

            # 4. Check and update A/B tests
            self.logger.info("Updating A/B tests...")
            ab_test_updates = await self._update_ab_tests()
            cycle_results["ab_test_updates"] = ab_test_updates

            # 5. Generate master recommendations
            self.logger.info("Generating master recommendations...")
            master_recommendations = await self._generate_master_recommendations(
                analytics_report,
                optimization_results,
                current_metrics,
            )
            cycle_results["recommendations"] = master_recommendations

            # 6. Check for critical alerts
            critical_alerts = await self._check_critical_conditions(current_metrics)
            cycle_results["alerts"] = critical_alerts

            # 7. Generate performance summary
            performance_summary = self._generate_performance_summary(
                analytics_report,
                optimization_results,
            )
            cycle_results["performance_summary"] = performance_summary

            # Store results for historical tracking
            self.performance_history.append(
                {
                    "timestamp": datetime.now(),
                    "performance_summary": performance_summary,
                    "key_metrics": self._extract_key_metrics(current_metrics),
                },
            )

            # Keep only last 30 days of history
            cutoff_date = datetime.now() - timedelta(days=30)
            self.performance_history = [
                h for h in self.performance_history if h["timestamp"] > cutoff_date
            ]

            self.logger.info("Complete analysis cycle finished successfully")

        except Exception as e:
            self.logger.error(f"Analysis cycle failed: {e}")
            cycle_results["error"] = str(e)

        return cycle_results

    async def _run_optimization_loop(self):
        """Background optimization loop"""
        optimization_interval = (
            self.config["optimization"]["run_frequency_hours"] * 3600
        )

        while self.is_running:
            try:
                self.logger.info("Running scheduled optimization cycle")

                # Get current metrics
                current_metrics = await self.analytics_engine.collect_all_metrics()

                # Run optimization
                optimization_results = (
                    await self.optimization_engine.run_optimization_cycle(
                        current_metrics,
                    )
                )

                # Store optimization history
                self.optimization_history.append(
                    {"timestamp": datetime.now(), "results": optimization_results},
                )

                # Check if we should auto-implement optimizations
                if self.config["automation"]["auto_optimize"]:
                    await self._auto_implement_optimizations(optimization_results)

                # Wait for next cycle
                await asyncio.sleep(optimization_interval)

            except Exception as e:
                self.logger.error(f"Optimization loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _run_ab_testing_automation(self):
        """Background A/B testing automation"""

        while self.is_running:
            try:
                # Check running tests
                running_tests = await self.ab_testing.get_running_tests()

                # Analyze completed tests
                for test in running_tests:
                    test_summary = await self.ab_testing.get_test_summary(test["id"])

                    if test_summary and test_summary["progress"] >= 1.0:
                        # Test has enough data - analyze results
                        analysis = await self.ab_testing.analyze_test_results(
                            test["id"],
                        )

                        if (
                            analysis
                            and self.config["ab_testing"]["auto_stop_conclusive_tests"]
                        ):
                            if (
                                analysis.statistical_significance
                                and analysis.practical_significance
                            ):
                                await self.ab_testing.stop_test(
                                    test["id"],
                                    "Conclusive results achieved",
                                )
                                self.logger.info(
                                    f"Auto-stopped conclusive test: {test['name']}",
                                )

                # Create new tests based on performance data
                if self.config["ab_testing"]["auto_create_tests"]:
                    await self._auto_create_ab_tests()

                # Wait 1 hour before next check
                await asyncio.sleep(3600)

            except Exception as e:
                self.logger.error(f"A/B testing automation error: {e}")
                await asyncio.sleep(300)

    async def _run_reporting_schedule(self):
        """Background reporting scheduler"""

        while self.is_running:
            try:
                current_time = datetime.now().strftime("%H:%M")

                # Executive summary
                if current_time == self.config["reporting"]["executive_summary_time"]:
                    await self._send_executive_summary()

                # Detailed report
                elif current_time == self.config["reporting"]["detailed_report_time"]:
                    await self._send_detailed_report()

                # Weekly deep dive (check if it's the right day)
                elif (
                    datetime.now().strftime("%A").lower()
                    == self.config["reporting"]["weekly_deep_dive"]
                    and current_time == "09:00"
                ):
                    await self._send_weekly_deep_dive()

                # Wait 1 minute before next check
                await asyncio.sleep(60)

            except Exception as e:
                self.logger.error(f"Reporting schedule error: {e}")
                await asyncio.sleep(60)

    async def _run_real_time_monitoring(self):
        """Real-time monitoring and alerting"""

        while self.is_running:
            try:
                # Collect current metrics
                current_metrics = await self.analytics_engine.collect_all_metrics()

                # Check for critical conditions
                alerts = await self._check_critical_conditions(current_metrics)

                # Send immediate alerts if needed
                for alert in alerts:
                    if alert["severity"] == "critical":
                        await self._send_immediate_alert(alert)

                # Wait 15 minutes before next check
                await asyncio.sleep(900)

            except Exception as e:
                self.logger.error(f"Real-time monitoring error: {e}")
                await asyncio.sleep(300)

    async def _update_ab_tests(self) -> dict:
        """Update and analyze all A/B tests"""
        update_results = {
            "tests_analyzed": 0,
            "tests_completed": 0,
            "significant_results": [],
            "recommendations": [],
        }

        try:
            running_tests = await self.ab_testing.get_running_tests()

            for test in running_tests:
                test_summary = await self.ab_testing.get_test_summary(test["id"])
                update_results["tests_analyzed"] += 1

                if test_summary and test_summary["progress"] >= 0.8:  # 80% complete
                    analysis = await self.ab_testing.analyze_test_results(test["id"])

                    if analysis:
                        if analysis.statistical_significance:
                            update_results["significant_results"].append(
                                {
                                    "test_name": test["name"],
                                    "effect_size": analysis.effect_size,
                                    "recommendation": analysis.recommendation,
                                },
                            )

                        if (
                            analysis.statistical_significance
                            and analysis.practical_significance
                        ):
                            update_results["tests_completed"] += 1
                            update_results["recommendations"].append(
                                f"Implement results from '{test['name']}': {
                                    analysis.recommendation
                                }",
                            )

        except Exception as e:
            self.logger.error(f"A/B test update failed: {e}")
            update_results["error"] = str(e)

        return update_results

    async def _generate_master_recommendations(
        self,
        analytics_report: PerformanceReport,
        optimization_results: dict,
        current_metrics: dict,
    ) -> list[dict]:
        """Generate master-level strategic recommendations"""

        recommendations = []

        # Extract key insights
        overall_score = current_metrics.get("performance_scores", {}).get(
            "overall_score",
            0,
        )
        engagement_rate = current_metrics.get("aggregated", {}).get(
            "average_engagement_rate",
            0,
        )
        viral_content = current_metrics.get("aggregated", {}).get(
            "total_viral_content",
            0,
        )

        # Strategic recommendations based on performance
        if overall_score < 50:
            recommendations.append(
                {
                    "type": "strategic",
                    "priority": "high",
                    "title": "Comprehensive Strategy Overhaul",
                    "description": "Overall performance is below expectations. Consider fundamental changes to content strategy, posting frequency, and platform focus.",
                    "expected_impact": 40.0,
                    "timeline": "2-4 weeks",
                    "effort": "high",
                },
            )

        elif overall_score < 70:
            recommendations.append(
                {
                    "type": "tactical",
                    "priority": "medium",
                    "title": "Performance Optimization",
                    "description": "Focus on improving top-performing content types and optimizing posting times.",
                    "expected_impact": 25.0,
                    "timeline": "1-2 weeks",
                    "effort": "medium",
                },
            )

        # Engagement-specific recommendations
        if engagement_rate < 2.0:
            recommendations.append(
                {
                    "type": "content",
                    "priority": "high",
                    "title": "Engagement Recovery Plan",
                    "description": "Implement interactive content formats, increase posting frequency, and focus on trending topics.",
                    "expected_impact": 30.0,
                    "timeline": "1 week",
                    "effort": "medium",
                },
            )

        # Viral content opportunities
        if viral_content == 0 and overall_score > 60:
            recommendations.append(
                {
                    "type": "growth",
                    "priority": "medium",
                    "title": "Viral Content Strategy",
                    "description": "Current performance suggests readiness for viral content. Focus on trending topics and shareable formats.",
                    "expected_impact": 50.0,
                    "timeline": "2-3 weeks",
                    "effort": "high",
                },
            )

        # Add optimization engine recommendations
        opt_recommendations = optimization_results.get("recommendations", [])
        for opt_rec in opt_recommendations:
            recommendations.append(
                {
                    "type": "optimization",
                    "priority": opt_rec.priority,
                    "title": "Optimization Opportunity",
                    "description": opt_rec.recommendation,
                    "expected_impact": opt_rec.expected_impact,
                    "timeline": "1 week",
                    "effort": opt_rec.implementation_effort,
                },
            )

        # Sort by priority and impact
        priority_order = {"high": 3, "medium": 2, "low": 1}
        recommendations.sort(
            key=lambda r: (priority_order.get(r["priority"], 1), r["expected_impact"]),
            reverse=True,
        )

        return recommendations[:10]  # Return top 10

    async def _check_critical_conditions(self, current_metrics: dict) -> list[dict]:
        """Check for critical performance conditions"""
        alerts = []

        # Performance drop alert
        if self.performance_history:
            latest_score = current_metrics.get("performance_scores", {}).get(
                "overall_score",
                0,
            )
            previous_score = self.performance_history[-1]["performance_summary"].get(
                "overall_score",
                0,
            )

            if previous_score > 0:
                performance_change = (
                    (latest_score - previous_score) / previous_score
                ) * 100

                if (
                    performance_change
                    < -self.config["thresholds"]["critical_performance_drop"]
                ):
                    alerts.append(
                        {
                            "type": "performance_drop",
                            "severity": "critical",
                            "message": f"Critical performance drop: {performance_change:.1f}%",
                            "current_score": latest_score,
                            "previous_score": previous_score,
                        },
                    )

        # Engagement rate alert
        engagement_rate = current_metrics.get("aggregated", {}).get(
            "average_engagement_rate",
            0,
        )
        if engagement_rate < 1.0:
            alerts.append(
                {
                    "type": "low_engagement",
                    "severity": "high",
                    "message": f"Very low engagement rate: {engagement_rate:.1f}%",
                    "threshold": 1.0,
                },
            )

        # Viral content detection
        viral_content = current_metrics.get("aggregated", {}).get(
            "total_viral_content",
            0,
        )
        if viral_content > 0:
            alerts.append(
                {
                    "type": "viral_content",
                    "severity": "positive",
                    "message": f"Viral content detected: {viral_content} pieces",
                    "action": "amplify",
                },
            )

        return alerts

    def _generate_performance_summary(
        self,
        analytics_report: PerformanceReport,
        optimization_results: dict,
    ) -> dict:
        """Generate high-level performance summary"""

        return {
            "overall_score": optimization_results.get("performance_scores", {}).get(
                "overall_score",
                0,
            ),
            "engagement_score": optimization_results.get("performance_scores", {}).get(
                "engagement_score",
                0,
            ),
            "growth_score": optimization_results.get("performance_scores", {}).get(
                "growth_score",
                0,
            ),
            "viral_score": optimization_results.get("performance_scores", {}).get(
                "viral_score",
                0,
            ),
            "optimization_actions": len(optimization_results.get("actions_taken", [])),
            "recommendations_count": len(
                optimization_results.get("recommendations", []),
            ),
            "alerts_count": len(analytics_report.alerts) if analytics_report else 0,
            "roi": (
                analytics_report.roi_analysis.get("roi_percentage", 0)
                if analytics_report
                else 0
            ),
        }

    def _extract_key_metrics(self, metrics: dict) -> dict:
        """Extract key metrics for historical tracking"""
        return {
            "total_followers": metrics.get("aggregated", {}).get("total_followers", 0),
            "total_impressions": metrics.get("aggregated", {}).get(
                "total_impressions",
                0,
            ),
            "average_engagement_rate": metrics.get("aggregated", {}).get(
                "average_engagement_rate",
                0,
            ),
            "viral_content_count": metrics.get("aggregated", {}).get(
                "total_viral_content",
                0,
            ),
            "overall_performance_score": metrics.get("performance_scores", {}).get(
                "overall_score",
                0,
            ),
        }

    async def _auto_implement_optimizations(self, optimization_results: dict):
        """Auto-implement low-risk optimizations"""

        for action in optimization_results.get("actions_taken", []):
            if (
                action.get("success")
                and action.get("impact_prediction", 0)
                > self.config["optimization"]["min_impact_threshold"]
            ):
                self.logger.info(
                    f"Auto-implementing optimization: {action['rule_name']}",
                )
                # Implementation would integrate with content management system

    async def _auto_create_ab_tests(self):
        """Automatically create A/B tests based on performance data"""

        # Check how many tests are currently running
        running_tests = await self.ab_testing.get_running_tests()

        if len(running_tests) >= self.config["ab_testing"]["max_concurrent_tests"]:
            return

        # Create tests for underperforming areas
        # This would analyze current performance and create relevant tests

    async def _send_executive_summary(self):
        """Send executive summary report"""
        try:
            cycle_results = await self.run_complete_analysis_cycle()
            # Format and send summary (integrate with Slack/email)
            self.logger.info("Executive summary sent")
        except Exception as e:
            self.logger.error(f"Failed to send executive summary: {e}")

    async def _send_detailed_report(self):
        """Send detailed analytics report"""
        try:
            analytics_report = await self.analytics_engine.generate_daily_report()
            # Format and send detailed report
            self.logger.info("Detailed report sent")
        except Exception as e:
            self.logger.error(f"Failed to send detailed report: {e}")

    async def _send_weekly_deep_dive(self):
        """Send weekly deep dive analysis"""
        try:
            # Generate comprehensive weekly analysis
            # Include trends, insights, and strategic recommendations
            self.logger.info("Weekly deep dive sent")
        except Exception as e:
            self.logger.error(f"Failed to send weekly deep dive: {e}")

    async def _send_immediate_alert(self, alert: dict):
        """Send immediate alert for critical conditions"""
        self.logger.critical(f"IMMEDIATE ALERT: {alert['message']}")
        # Integrate with alerting systems (Slack, email, SMS, etc.)

    async def get_system_health(self) -> dict:
        """Get comprehensive system health status"""

        try:
            # Get running tests
            running_tests = await self.ab_testing.get_running_tests()

            # Calculate performance trend
            trend = "stable"
            if len(self.performance_history) >= 2:
                recent = self.performance_history[-1]["performance_summary"][
                    "overall_score"
                ]
                previous = self.performance_history[-2]["performance_summary"][
                    "overall_score"
                ]
                change = ((recent - previous) / previous) * 100 if previous > 0 else 0

                if change > 5:
                    trend = "improving"
                elif change < -5:
                    trend = "declining"

            return {
                "system_running": self.is_running,
                "background_tasks": len(self.background_tasks),
                "performance_trend": trend,
                "running_ab_tests": len(running_tests),
                "optimization_history": len(self.optimization_history),
                "last_analysis": (
                    self.performance_history[-1]["timestamp"]
                    if self.performance_history
                    else None
                ),
                "health_score": (
                    85.0 if self.is_running else 0.0
                ),  # Simplified health score
            }

        except Exception as e:
            self.logger.error(f"System health check failed: {e}")
            return {"error": str(e), "health_score": 0.0}


# CLI Interface


async def main():
    """Main CLI interface for analytics master"""
    import argparse

    parser = argparse.ArgumentParser(description="Analytics & Optimization Master")
    parser.add_argument("command", choices=["start", "analyze", "health", "report"])
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument(
        "--duration",
        type=int,
        default=24,
        help="Run duration in hours (for start command)",
    )

    args = parser.parse_args()

    # Initialize master controller
    master = AnalyticsMasterController(args.config)

    try:
        if args.command == "start":
            print("Starting Analytics Master System...")
            await master.start_master_system()

            # Run for specified duration
            run_time = args.duration * 3600  # Convert to seconds
            await asyncio.sleep(run_time)

            await master.stop_master_system()
            print("Analytics Master System stopped")

        elif args.command == "analyze":
            print("Running complete analysis cycle...")
            results = await master.run_complete_analysis_cycle()

            print("\n=== ANALYSIS RESULTS ===")
            print(f"Timestamp: {results['timestamp']}")
            print(
                f"Performance Score: {
                    results['performance_summary'].get('overall_score', 0):.1f}/100",
            )
            print(
                f"Optimization Actions: {
                    results['performance_summary'].get('optimization_actions', 0)
                }",
            )
            print(f"Recommendations: {len(results['recommendations'])}")
            print(f"Alerts: {len(results['alerts'])}")

            if results["recommendations"]:
                print("\nTop Recommendations:")
                for i, rec in enumerate(results["recommendations"][:3], 1):
                    print(
                        f"  {i}. {rec['title']} (Impact: +{
                            rec['expected_impact']:.1f}%)",
                    )

        elif args.command == "health":
            health = await master.get_system_health()
            print(f"System Health: {json.dumps(health, indent=2, default=str)}")

        elif args.command == "report":
            print("Generating comprehensive report...")
            analytics_report = await master.analytics_engine.generate_daily_report()

            print("\n=== DAILY REPORT ===")
            print(f"Date: {analytics_report.date}")
            print(f"Executive Summary: {analytics_report.executive_summary}")
            print(f"Recommendations: {len(analytics_report.recommendations)}")
            print(f"Alerts: {len(analytics_report.alerts)}")
            print(f"ROI: {analytics_report.roi_analysis.get('roi_percentage', 0):.1f}%")

    except KeyboardInterrupt:
        print("\nStopping...")
        if master.is_running:
            await master.stop_master_system()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
