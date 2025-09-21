#!/usr/bin/env python3
"""
Vibe Analytics & Optimization Engine
Comprehensive performance tracking, analysis, and optimization system
"""

import asyncio
import json
import logging
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# Visualization and reporting
try:
    import matplotlib.pyplot as plt
    import openai
    import plotly.express as px
    import plotly.graph_objects as go
    import requests
    import seaborn as sns
    from jinja2 import Template
    from plotly.subplots import make_subplots
    from slack_sdk import WebClient
except ImportError as e:
    print(f"Analytics dependencies not installed: {e}")
    print("Run: pip install plotly seaborn matplotlib slack-sdk openai jinja2")


@dataclass
class MetricSnapshot:
    """Single metric measurement at a point in time"""

    metric_name: str
    value: float
    timestamp: datetime
    platform: str
    metadata: dict = None


@dataclass
class PerformanceReport:
    """Comprehensive performance report"""

    date: str
    executive_summary: str
    content_performance: dict
    conversion_metrics: dict
    ai_agent_performance: dict
    social_growth: dict
    recommendations: list[str]
    visualizations: dict
    alerts: list[str]
    roi_analysis: dict


class VibeAnalyticsEngine:
    """Main analytics and optimization engine"""

    def __init__(self, config_path: str = None):
        """Initialize analytics engine"""
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()

        # Initialize database
        self.db_path = "analytics_engine.db"
        self._init_database()

        # Platform clients
        self.clients = self._initialize_clients()

        # Metrics configuration
        self.tracking_metrics = self._initialize_metrics()
        self.optimization_rules = self._load_optimization_rules()

        # AI components
        self.openai_client = None
        if self.config.get("openai_api_key"):
            openai.api_key = self.config["openai_api_key"]
            self.openai_client = openai

        self.logger.info("Vibe Analytics Engine initialized successfully")

    def _load_config(self, config_path: str = None) -> dict:
        """Load configuration from file or environment"""
        default_config = {
            "slack_token": os.getenv("SLACK_BOT_TOKEN"),
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "channels": {
                "alerts": "#vibe-alerts",
                "reports": "#vibe-analytics",
                "team": "#team-updates",
            },
            "thresholds": {
                "viral_views": 100000,
                "high_engagement": 5.0,
                "low_engagement": 1.0,
                "conversion_drop": 20.0,
            },
            "platforms": {
                "twitter": {"enabled": True, "weight": 1.0},
                "instagram": {"enabled": True, "weight": 1.2},
                "tiktok": {"enabled": True, "weight": 1.5},
                "linkedin": {"enabled": True, "weight": 0.8},
                "reddit": {"enabled": True, "weight": 0.9},
            },
        }

        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        log_dir = Path("../logs")
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_dir / "analytics_engine.log"),
                logging.StreamHandler(),
            ],
        )

        return logging.getLogger(__name__)

    def _init_database(self):
        """Initialize SQLite database for analytics storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp DATETIME NOT NULL,
                platform TEXT NOT NULL,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_metric_platform (metric_name, platform),
                INDEX idx_timestamp (timestamp)
            )
        """,
        )

        # Performance reports table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS performance_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                report_type TEXT DEFAULT 'daily',
                report_data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, report_type)
            )
        """,
        )

        # Optimization rules table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS optimization_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL,
                condition_sql TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_config TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # A/B tests table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ab_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                variant_a TEXT NOT NULL,
                variant_b TEXT NOT NULL,
                metric_target TEXT NOT NULL,
                start_date DATETIME NOT NULL,
                end_date DATETIME,
                status TEXT DEFAULT 'active',
                results TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # Alerts table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                platform TEXT,
                metric_name TEXT,
                threshold_value REAL,
                actual_value REAL,
                acknowledged BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_alert_type (alert_type),
                INDEX idx_acknowledged (acknowledged)
            )
        """,
        )

        conn.commit()
        conn.close()

    def _initialize_clients(self) -> dict:
        """Initialize platform API clients"""
        clients = {}

        # Slack client
        if self.config.get("slack_token"):
            try:
                clients["slack"] = WebClient(token=self.config["slack_token"])
                self.logger.info("Slack client initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Slack client: {e}")

        # Import social media clients from our existing modules
        try:
            from social_distributor import SocialMediaDistributor

            clients["social"] = SocialMediaDistributor()

            from social_analytics_dashboard import SocialAnalyticsDashboard

            clients["social_analytics"] = SocialAnalyticsDashboard()

            self.logger.info("Social media clients initialized")
        except ImportError as e:
            self.logger.warning(f"Social media modules not available: {e}")

        return clients

    def _initialize_metrics(self) -> dict:
        """Define comprehensive metrics tracking structure"""
        return {
            "content_performance": {
                "views": {"target": 10000, "weight": 1.0},
                "engagement_rate": {"target": 5.0, "weight": 2.0},
                "share_rate": {"target": 2.0, "weight": 1.5},
                "completion_rate": {"target": 75.0, "weight": 1.2},
                "ctr": {"target": 3.0, "weight": 1.8},
                "saves": {"target": 500, "weight": 1.3},
                "comments_sentiment": {"target": 0.6, "weight": 1.1},
            },
            "conversion_metrics": {
                "leads_generated": {"target": 100, "weight": 2.5},
                "qualified_leads": {"target": 30, "weight": 3.0},
                "demos_scheduled": {"target": 15, "weight": 3.5},
                "deals_closed": {"target": 5, "weight": 5.0},
                "revenue": {"target": 50000, "weight": 4.0},
                "cost_per_lead": {"target": 25, "weight": 2.0, "inverse": True},
                "ltv_cac_ratio": {"target": 3.0, "weight": 3.0},
            },
            "ai_agent_performance": {
                "calls_made": {"target": 200, "weight": 1.0},
                "conversations_completed": {"target": 150, "weight": 1.5},
                "positive_responses": {"target": 100, "weight": 2.0},
                "appointments_set": {"target": 20, "weight": 3.0},
                "average_call_duration": {"target": 180, "weight": 1.2},
                "conversion_rate": {"target": 15.0, "weight": 2.5},
                "objection_handling_score": {"target": 8.0, "weight": 1.8},
            },
            "social_growth": {
                "followers_gained": {"target": 1000, "weight": 1.5},
                "reach": {"target": 50000, "weight": 1.2},
                "impressions": {"target": 100000, "weight": 1.0},
                "mentions": {"target": 50, "weight": 1.3},
                "brand_sentiment": {"target": 0.7, "weight": 2.0},
                "viral_content_count": {"target": 2, "weight": 2.5},
            },
            "business_metrics": {
                "website_traffic": {"target": 10000, "weight": 1.5},
                "bounce_rate": {"target": 40.0, "weight": 1.2, "inverse": True},
                "session_duration": {"target": 120, "weight": 1.3},
                "conversion_rate": {"target": 2.5, "weight": 3.0},
                "customer_satisfaction": {"target": 4.5, "weight": 2.0},
            },
        }

    def _load_optimization_rules(self) -> list[dict]:
        """Load optimization rules from database or defaults"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM optimization_rules WHERE active = TRUE")
            rules = []

            for row in cursor.fetchall():
                rules.append(
                    {
                        "id": row[0],
                        "name": row[1],
                        "condition_sql": row[2],
                        "action_type": row[3],
                        "action_config": json.loads(row[4]) if row[4] else {},
                        "active": bool(row[5]),
                    },
                )

            conn.close()
            return rules

        except Exception as e:
            self.logger.error(f"Failed to load optimization rules: {e}")
            return self._get_default_optimization_rules()

    def _get_default_optimization_rules(self) -> list[dict]:
        """Default optimization rules"""
        return [
            {
                "name": "Low Engagement Alert",
                "condition_sql": "engagement_rate < 1.0",
                "action_type": "alert",
                "action_config": {"severity": "medium", "channel": "alerts"},
            },
            {
                "name": "Viral Content Detected",
                "condition_sql": "views > 100000",
                "action_type": "boost",
                "action_config": {
                    "increase_posting_frequency": True,
                    "similar_content": True,
                },
            },
            {
                "name": "Conversion Drop",
                "condition_sql": "conversion_rate < 1.0",
                "action_type": "alert",
                "action_config": {"severity": "high", "notify_team": True},
            },
        ]

    async def collect_all_metrics(self) -> dict[str, Any]:
        """Collect comprehensive metrics from all platforms"""
        self.logger.info("Starting comprehensive metrics collection")

        all_metrics = {
            "timestamp": datetime.now(UTC),
            "platforms": {},
            "aggregated": {},
            "performance_scores": {},
        }

        # Collect from each enabled platform
        collection_tasks = []

        for platform, config in self.config["platforms"].items():
            if config["enabled"]:
                task = asyncio.create_task(self._collect_platform_metrics(platform))
                collection_tasks.append((platform, task))

        # Execute collections concurrently
        for platform, task in collection_tasks:
            try:
                metrics = await task
                all_metrics["platforms"][platform] = metrics
                await self._store_platform_metrics(platform, metrics)
            except Exception as e:
                self.logger.error(f"Failed to collect metrics for {platform}: {e}")
                all_metrics["platforms"][platform] = {"error": str(e)}

        # Calculate aggregated metrics
        all_metrics["aggregated"] = self._calculate_aggregated_metrics(
            all_metrics["platforms"],
        )

        # Calculate performance scores
        all_metrics["performance_scores"] = self._calculate_performance_scores(
            all_metrics["aggregated"],
        )

        self.logger.info("Metrics collection completed successfully")
        return all_metrics

    async def _collect_platform_metrics(self, platform: str) -> dict:
        """Collect metrics from a specific platform"""

        if platform == "twitter":
            return await self._collect_twitter_metrics()
        if platform == "instagram":
            return await self._collect_instagram_metrics()
        if platform == "tiktok":
            return await self._collect_tiktok_metrics()
        if platform == "linkedin":
            return await self._collect_linkedin_metrics()
        if platform == "reddit":
            return await self._collect_reddit_metrics()
        return {"error": f"Unsupported platform: {platform}"}

    async def _collect_twitter_metrics(self) -> dict:
        """Collect Twitter/X metrics"""
        try:
            if "social_analytics" not in self.clients:
                return {"error": "Social analytics client not available"}

            # Use existing social analytics dashboard
            client = self.clients["social_analytics"]

            # Get recent metrics (last 24 hours)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)

            # This would integrate with our existing analytics system
            metrics = {
                "followers": await self._get_follower_count("twitter"),
                "engagement_rate": await self._get_engagement_rate("twitter"),
                "impressions": await self._get_impressions("twitter"),
                "mentions": await self._get_mentions_count("twitter"),
                "top_posts": await self._get_top_posts("twitter", limit=5),
            }

            return metrics

        except Exception as e:
            self.logger.error(f"Twitter metrics collection failed: {e}")
            return {"error": str(e)}

    async def _collect_instagram_metrics(self) -> dict:
        """Collect Instagram metrics"""
        try:
            metrics = {
                "followers": await self._get_follower_count("instagram"),
                "engagement_rate": await self._get_engagement_rate("instagram"),
                "reach": await self._get_reach("instagram"),
                "story_views": await self._get_story_views("instagram"),
                "reels_performance": await self._get_reels_metrics("instagram"),
            }

            return metrics

        except Exception as e:
            self.logger.error(f"Instagram metrics collection failed: {e}")
            return {"error": str(e)}

    async def _collect_tiktok_metrics(self) -> dict:
        """Collect TikTok metrics"""
        try:
            metrics = {
                "followers": await self._get_follower_count("tiktok"),
                "views": await self._get_total_views("tiktok"),
                "engagement_rate": await self._get_engagement_rate("tiktok"),
                "viral_videos": await self._get_viral_content("tiktok"),
                "trending_hashtags": await self._get_trending_hashtags("tiktok"),
            }

            return metrics

        except Exception as e:
            self.logger.error(f"TikTok metrics collection failed: {e}")
            return {"error": str(e)}

    async def _collect_linkedin_metrics(self) -> dict:
        """Collect LinkedIn metrics"""
        try:
            metrics = {
                "connections": await self._get_connections_count("linkedin"),
                "post_impressions": await self._get_impressions("linkedin"),
                "engagement_rate": await self._get_engagement_rate("linkedin"),
                "profile_views": await self._get_profile_views("linkedin"),
                "lead_generation": await self._get_lead_metrics("linkedin"),
            }

            return metrics

        except Exception as e:
            self.logger.error(f"LinkedIn metrics collection failed: {e}")
            return {"error": str(e)}

    async def _collect_reddit_metrics(self) -> dict:
        """Collect Reddit metrics"""
        try:
            metrics = {
                "post_karma": await self._get_karma_score("reddit"),
                "upvotes": await self._get_total_upvotes("reddit"),
                "comments": await self._get_comment_count("reddit"),
                "subreddit_growth": await self._get_subreddit_metrics("reddit"),
                "trending_posts": await self._get_trending_posts("reddit"),
            }

            return metrics

        except Exception as e:
            self.logger.error(f"Reddit metrics collection failed: {e}")
            return {"error": str(e)}

    # Platform-specific metric getters (simplified implementations)
    async def _get_follower_count(self, platform: str) -> int:
        """Get follower count for platform"""
        # This would integrate with actual platform APIs
        # For now, return simulated data
        base_counts = {
            "twitter": 5000,
            "instagram": 3000,
            "tiktok": 8000,
            "linkedin": 1500,
            "reddit": 2000,
        }

        # Add some realistic variation
        import random

        variation = random.randint(-50, 100)
        return base_counts.get(platform, 1000) + variation

    async def _get_engagement_rate(self, platform: str) -> float:
        """Get engagement rate for platform"""
        import random

        return round(random.uniform(1.5, 8.0), 2)

    async def _get_impressions(self, platform: str) -> int:
        """Get impressions for platform"""
        import random

        return random.randint(10000, 100000)

    async def _get_mentions_count(self, platform: str) -> int:
        """Get mentions count"""
        import random

        return random.randint(10, 100)

    async def _get_top_posts(self, platform: str, limit: int = 5) -> list[dict]:
        """Get top performing posts"""
        # Simulated top posts
        import random

        posts = []
        for i in range(limit):
            posts.append(
                {
                    "id": f"{platform}_post_{i + 1}",
                    "content": f"Sample high-performing post #{i + 1}",
                    "views": random.randint(50000, 500000),
                    "likes": random.randint(1000, 10000),
                    "shares": random.randint(100, 1000),
                    "engagement_rate": round(random.uniform(3.0, 12.0), 2),
                },
            )
        return posts

    # Additional metric getters would be implemented similarly...
    async def _get_reach(self, platform: str) -> int:
        import random

        return random.randint(20000, 200000)

    async def _get_story_views(self, platform: str) -> int:
        import random

        return random.randint(5000, 50000)

    async def _get_reels_metrics(self, platform: str) -> dict:
        import random

        return {
            "total_reels": random.randint(10, 50),
            "average_views": random.randint(25000, 250000),
            "completion_rate": round(random.uniform(60.0, 90.0), 2),
        }

    async def _get_total_views(self, platform: str) -> int:
        import random

        return random.randint(500000, 5000000)

    async def _get_viral_content(self, platform: str) -> list[dict]:
        import random

        viral_threshold = self.config["thresholds"]["viral_views"]

        viral_posts = []
        for i in range(random.randint(1, 5)):
            viral_posts.append(
                {
                    "id": f"viral_{platform}_{i + 1}",
                    "views": random.randint(viral_threshold, viral_threshold * 10),
                    "engagement_rate": round(random.uniform(8.0, 25.0), 2),
                },
            )

        return viral_posts

    async def _get_trending_hashtags(self, platform: str) -> list[str]:
        trending = [
            "#productivity",
            "#AI",
            "#automation",
            "#business",
            "#growth",
            "#viral",
            "#trending",
        ]
        import random

        return random.sample(trending, k=min(5, len(trending)))

    def _calculate_aggregated_metrics(self, platform_metrics: dict) -> dict:
        """Calculate aggregated metrics across all platforms"""
        aggregated = {
            "total_followers": 0,
            "total_impressions": 0,
            "average_engagement_rate": 0.0,
            "total_viral_content": 0,
            "platform_performance": {},
        }

        valid_platforms = 0
        total_engagement = 0.0

        for platform, metrics in platform_metrics.items():
            if "error" not in metrics:
                valid_platforms += 1

                # Sum followers
                if "followers" in metrics:
                    aggregated["total_followers"] += metrics["followers"]

                # Sum impressions
                if "impressions" in metrics:
                    aggregated["total_impressions"] += metrics["impressions"]
                elif "views" in metrics:
                    aggregated["total_impressions"] += metrics["views"]

                # Average engagement rate
                if "engagement_rate" in metrics:
                    total_engagement += metrics["engagement_rate"]

                # Count viral content
                viral_content = metrics.get(
                    "viral_videos",
                    metrics.get("viral_content", []),
                )
                if isinstance(viral_content, list):
                    aggregated["total_viral_content"] += len(viral_content)

                # Platform performance score
                platform_weight = self.config["platforms"][platform].get("weight", 1.0)
                performance_score = self._calculate_platform_performance_score(metrics)
                aggregated["platform_performance"][platform] = {
                    "score": performance_score,
                    "weight": platform_weight,
                    "weighted_score": performance_score * platform_weight,
                }

        # Calculate averages
        if valid_platforms > 0:
            aggregated["average_engagement_rate"] = total_engagement / valid_platforms

        return aggregated

    def _calculate_platform_performance_score(self, metrics: dict) -> float:
        """Calculate performance score for a platform (0-100)"""
        score = 0.0
        max_score = 100.0

        # Engagement rate component (40 points)
        engagement = metrics.get("engagement_rate", 0)
        if engagement >= 5.0:
            score += 40
        elif engagement >= 3.0:
            score += 30
        elif engagement >= 1.5:
            score += 20
        else:
            score += 10

        # Growth component (30 points)
        followers = metrics.get("followers", 0)
        if followers >= 10000:
            score += 30
        elif followers >= 5000:
            score += 25
        elif followers >= 1000:
            score += 15
        else:
            score += 5

        # Viral content component (20 points)
        viral_content = metrics.get("viral_videos", metrics.get("viral_content", []))
        viral_count = len(viral_content) if isinstance(viral_content, list) else 0
        if viral_count >= 3:
            score += 20
        elif viral_count >= 1:
            score += 15
        else:
            score += 5

        # Reach/Impressions component (10 points)
        reach = metrics.get(
            "impressions",
            metrics.get("views", metrics.get("reach", 0)),
        )
        if reach >= 100000:
            score += 10
        elif reach >= 50000:
            score += 8
        elif reach >= 10000:
            score += 5
        else:
            score += 2

        return min(score, max_score)

    def _calculate_performance_scores(self, aggregated_metrics: dict) -> dict:
        """Calculate overall performance scores"""
        scores = {
            "overall_score": 0.0,
            "content_score": 0.0,
            "growth_score": 0.0,
            "engagement_score": 0.0,
            "viral_score": 0.0,
        }

        # Content performance score
        avg_engagement = aggregated_metrics.get("average_engagement_rate", 0)
        if avg_engagement >= 5.0:
            scores["engagement_score"] = 100
        else:
            scores["engagement_score"] = (avg_engagement / 5.0) * 100

        # Growth score based on followers
        total_followers = aggregated_metrics.get("total_followers", 0)
        scores["growth_score"] = min((total_followers / 50000) * 100, 100)

        # Viral content score
        viral_count = aggregated_metrics.get("total_viral_content", 0)
        scores["viral_score"] = min(viral_count * 25, 100)

        # Overall weighted score
        scores["overall_score"] = (
            scores["engagement_score"] * 0.4
            + scores["growth_score"] * 0.3
            + scores["viral_score"] * 0.3
        )

        return scores

    async def _store_platform_metrics(self, platform: str, metrics: dict):
        """Store platform metrics in database"""
        if "error" in metrics:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        timestamp = datetime.now(UTC)

        # Store individual metrics
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                cursor.execute(
                    """
                    INSERT INTO metrics (metric_name, value, timestamp, platform, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (metric_name, value, timestamp, platform, json.dumps(metrics)),
                )

        conn.commit()
        conn.close()

    async def generate_daily_report(self) -> PerformanceReport:
        """Generate comprehensive daily performance report"""
        self.logger.info("Generating daily performance report")

        # Collect all current metrics
        all_metrics = await self.collect_all_metrics()

        # Generate executive summary
        executive_summary = await self._generate_executive_summary(all_metrics)

        # Analyze different aspects
        content_analysis = self._analyze_content_performance(all_metrics)
        conversion_analysis = await self._analyze_conversion_funnel(all_metrics)
        ai_performance = await self._analyze_ai_agent_performance(all_metrics)
        social_growth = self._analyze_social_growth(all_metrics)

        # Generate AI recommendations
        recommendations = await self._generate_ai_recommendations(all_metrics)

        # Create visualizations
        visualizations = await self._create_visualizations(all_metrics)

        # Check for alerts
        alerts = await self._check_alert_conditions(all_metrics)

        # Calculate ROI analysis
        roi_analysis = self._calculate_roi_analysis(all_metrics)

        # Create report object
        report = PerformanceReport(
            date=datetime.now().strftime("%Y-%m-%d"),
            executive_summary=executive_summary,
            content_performance=content_analysis,
            conversion_metrics=conversion_analysis,
            ai_agent_performance=ai_performance,
            social_growth=social_growth,
            recommendations=recommendations,
            visualizations=visualizations,
            alerts=alerts,
            roi_analysis=roi_analysis,
        )

        # Store report
        await self._store_report(report)

        # Send notifications
        if self.config.get("slack_token"):
            await self._send_slack_report(report)

        self.logger.info("Daily report generated successfully")
        return report

    async def _generate_executive_summary(self, metrics: dict) -> str:
        """Generate AI-powered executive summary"""

        summary_data = {
            "total_followers": metrics["aggregated"].get("total_followers", 0),
            "total_impressions": metrics["aggregated"].get("total_impressions", 0),
            "average_engagement": metrics["aggregated"].get(
                "average_engagement_rate",
                0,
            ),
            "viral_content": metrics["aggregated"].get("total_viral_content", 0),
            "overall_score": metrics["performance_scores"].get("overall_score", 0),
            "top_platform": max(
                metrics["aggregated"].get("platform_performance", {}),
                key=lambda x: metrics["aggregated"]["platform_performance"][x][
                    "weighted_score"
                ],
                default="N/A",
            ),
        }

        # Generate summary with AI or template
        if self.openai_client:
            try:
                prompt = f"""
                Generate a concise executive summary for today's social media performance:

                Key Metrics:
                - Total Followers: {summary_data["total_followers"]:,}
                - Total Impressions: {summary_data["total_impressions"]:,}
                - Average Engagement Rate: {summary_data["average_engagement"]:.1f}%
                - Viral Content Created: {summary_data["viral_content"]}
                - Overall Performance Score: {summary_data["overall_score"]:.1f}/100
                - Top Performing Platform: {summary_data["top_platform"]}

                Keep it to 2-3 sentences, focus on the most important insights and trends.
                """

                response = await self.openai_client.ChatCompletion.acreate(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                )

                return response.choices[0].message.content.strip()

            except Exception as e:
                self.logger.error(f"Failed to generate AI summary: {e}")

        # Fallback template-based summary
        if summary_data["overall_score"] >= 80:
            performance = "excellent"
        elif summary_data["overall_score"] >= 60:
            performance = "good"
        elif summary_data["overall_score"] >= 40:
            performance = "moderate"
        else:
            performance = "needs improvement"

        return f"""
        Today's social media performance was {performance} with an overall score of {
            summary_data["overall_score"]:.1f}/100.
        We reached {
            summary_data["total_impressions"]:,
        } people across all platforms with an average engagement rate of {
            summary_data["average_engagement"]:.1f}%.
        {
            summary_data["top_platform"].title()
        } was our top performing platform, and we created {
            summary_data["viral_content"]
        } pieces of viral content.
        """.strip()

    def _analyze_content_performance(self, metrics: dict) -> dict:
        """Analyze content performance across platforms"""
        analysis = {
            "top_performing_content": [],
            "viral_coefficient": 0.0,
            "engagement_trends": {},
            "optimal_posting_times": {},
            "content_type_performance": {},
            "platform_breakdown": {},
        }

        total_engagement = 0
        total_reach = 0
        viral_posts = []

        # Analyze each platform
        for platform, data in metrics["platforms"].items():
            if "error" not in data:
                platform_analysis = {
                    "engagement_rate": data.get("engagement_rate", 0),
                    "reach": data.get(
                        "impressions",
                        data.get("views", data.get("reach", 0)),
                    ),
                    "viral_content_count": 0,
                }

                # Check for viral content
                viral_content = data.get("viral_videos", data.get("viral_content", []))
                if isinstance(viral_content, list):
                    platform_analysis["viral_content_count"] = len(viral_content)
                    viral_posts.extend(viral_content)

                # Get top posts if available
                top_posts = data.get("top_posts", [])
                if top_posts:
                    analysis["top_performing_content"].extend(top_posts)

                analysis["platform_breakdown"][platform] = platform_analysis

                total_engagement += platform_analysis["engagement_rate"]
                total_reach += platform_analysis["reach"]

        # Calculate viral coefficient
        if total_reach > 0:
            total_shares = sum(
                post.get("shares", 0) for post in analysis["top_performing_content"]
            )
            analysis["viral_coefficient"] = total_shares / total_reach

        return analysis

    async def _analyze_conversion_funnel(self, metrics: dict) -> dict:
        """Analyze conversion funnel metrics"""
        # This would integrate with CRM/sales data
        # For now, return simulated conversion analysis

        import random

        funnel_data = {
            "impressions": metrics["aggregated"].get("total_impressions", 0),
            "clicks": random.randint(1000, 5000),
            "leads": random.randint(100, 500),
            "qualified_leads": random.randint(30, 150),
            "demos_scheduled": random.randint(10, 50),
            "deals_closed": random.randint(2, 15),
            "revenue": random.randint(10000, 100000),
        }

        # Calculate conversion rates
        conversion_rates = {}
        stages = list(funnel_data.keys())

        for i in range(len(stages) - 1):
            current_stage = funnel_data[stages[i]]
            next_stage = funnel_data[stages[i + 1]]

            if current_stage > 0:
                conversion_rates[f"{stages[i]}_to_{stages[i + 1]}"] = (
                    next_stage / current_stage
                ) * 100

        return {
            "funnel_data": funnel_data,
            "conversion_rates": conversion_rates,
            "total_conversion_rate": (
                funnel_data["deals_closed"] / max(funnel_data["impressions"], 1)
            )
            * 100,
            "cost_per_lead": 50.0,  # Would calculate from actual ad spend
            "ltv_cac_ratio": 3.2,  # Would calculate from actual customer data
            "revenue_attribution": {
                "organic_social": 40,
                "paid_social": 35,
                "direct": 15,
                "referral": 10,
            },
        }

    async def _analyze_ai_agent_performance(self, metrics: dict) -> dict:
        """Analyze AI agent performance metrics"""
        # This would integrate with Vapi or other AI calling platforms
        # For now, return simulated AI performance data

        import random

        ai_metrics = {
            "calls_made": random.randint(150, 300),
            "conversations_completed": random.randint(100, 250),
            "positive_responses": random.randint(60, 150),
            "appointments_set": random.randint(15, 40),
            "average_call_duration": random.randint(120, 300),
            "objection_handling_score": round(random.uniform(7.0, 9.5), 1),
            "sentiment_analysis": {
                "positive": random.randint(40, 70),
                "neutral": random.randint(20, 40),
                "negative": random.randint(5, 20),
            },
            "top_objections": [
                "Price concerns",
                "Not the right time",
                "Need to think about it",
                "Already have a solution",
                "Budget constraints",
            ],
        }

        # Calculate conversion rates
        if ai_metrics["calls_made"] > 0:
            ai_metrics["conversation_rate"] = (
                ai_metrics["conversations_completed"] / ai_metrics["calls_made"]
            ) * 100
            ai_metrics["appointment_rate"] = (
                ai_metrics["appointments_set"] / ai_metrics["calls_made"]
            ) * 100

        return ai_metrics

    def _analyze_social_growth(self, metrics: dict) -> dict:
        """Analyze social media growth metrics"""
        growth_analysis = {
            "follower_growth": {},
            "engagement_growth": {},
            "reach_expansion": {},
            "viral_content_impact": {},
            "platform_momentum": {},
        }

        for platform, data in metrics["platforms"].items():
            if "error" not in data:
                # Simulate growth calculations (would use historical data in production)
                import random

                growth_analysis["follower_growth"][platform] = {
                    "current": data.get("followers", 0),
                    "growth_rate": round(random.uniform(-2.0, 15.0), 2),
                    "growth_velocity": round(random.uniform(0.5, 3.0), 2),
                }

                growth_analysis["engagement_growth"][platform] = {
                    "current_rate": data.get("engagement_rate", 0),
                    "trend": random.choice(["increasing", "stable", "decreasing"]),
                    "momentum_score": round(random.uniform(6.0, 9.5), 1),
                }

        return growth_analysis

    async def _generate_ai_recommendations(self, metrics: dict) -> list[str]:
        """Generate AI-powered recommendations"""

        if not self.openai_client:
            return self._generate_template_recommendations(metrics)

        try:
            # Prepare metrics summary for AI
            metrics_summary = {
                "performance_scores": metrics["performance_scores"],
                "platform_performance": metrics["aggregated"].get(
                    "platform_performance",
                    {},
                ),
                "engagement_rate": metrics["aggregated"].get(
                    "average_engagement_rate",
                    0,
                ),
                "viral_content": metrics["aggregated"].get("total_viral_content", 0),
            }

            prompt = f"""
            Based on these social media performance metrics, generate 5 specific, actionable recommendations:

            {json.dumps(metrics_summary, indent=2)}

            Focus on:
            1. Content strategy improvements
            2. Platform optimization
            3. Engagement tactics
            4. Growth strategies
            5. Conversion optimization

            Be specific with numbers, tactics, and timelines. Each recommendation should be 1-2 sentences.
            """

            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )

            content = response.choices[0].message.content.strip()

            # Parse recommendations (split by numbers)
            import re

            recommendations = re.split(r"\d+\.", content)
            recommendations = [rec.strip() for rec in recommendations if rec.strip()]

            return recommendations[:5]  # Return top 5

        except Exception as e:
            self.logger.error(f"Failed to generate AI recommendations: {e}")
            return self._generate_template_recommendations(metrics)

    def _generate_template_recommendations(self, metrics: dict) -> list[str]:
        """Generate template-based recommendations"""
        recommendations = []

        overall_score = metrics["performance_scores"].get("overall_score", 0)
        engagement_rate = metrics["aggregated"].get("average_engagement_rate", 0)
        viral_count = metrics["aggregated"].get("total_viral_content", 0)

        # Performance-based recommendations
        if overall_score < 50:
            recommendations.append(
                "Focus on improving content quality and consistency across all platforms",
            )

        if engagement_rate < 3.0:
            recommendations.append(
                "Increase posting frequency and use more interactive content formats (polls, Q&A, stories)",
            )

        if viral_count == 0:
            recommendations.append(
                "Analyze trending topics and create content around current viral themes",
            )

        # Platform-specific recommendations
        platform_performance = metrics["aggregated"].get("platform_performance", {})
        if platform_performance:
            best_platform = max(
                platform_performance.keys(),
                key=lambda x: platform_performance[x]["weighted_score"],
            )
            recommendations.append(
                f"Double down on {best_platform} content as it's showing the highest performance",
            )

        recommendations.append(
            "Implement A/B testing for post timing and content formats",
        )

        return recommendations[:5]

    async def _create_visualizations(self, metrics: dict) -> dict:
        """Create interactive visualizations"""
        visualizations = {}

        try:
            # Performance scores radar chart
            scores = metrics["performance_scores"]
            categories = ["Engagement", "Growth", "Viral Content", "Overall"]
            values = [
                scores.get("engagement_score", 0),
                scores.get("growth_score", 0),
                scores.get("viral_score", 0),
                scores.get("overall_score", 0),
            ]

            fig_radar = go.Figure()
            fig_radar.add_trace(
                go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill="toself",
                    name="Performance Scores",
                ),
            )
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True,
                title="Performance Score Breakdown",
            )
            visualizations["performance_radar"] = fig_radar.to_html(
                include_plotlyjs="cdn",
            )

            # Platform comparison bar chart
            platform_data = metrics["aggregated"].get("platform_performance", {})
            if platform_data:
                platforms = list(platform_data.keys())
                scores = [platform_data[p]["weighted_score"] for p in platforms]

                fig_bar = go.Figure(
                    data=[go.Bar(x=platforms, y=scores, name="Platform Performance")],
                )
                fig_bar.update_layout(
                    title="Platform Performance Comparison",
                    xaxis_title="Platform",
                    yaxis_title="Weighted Score",
                )
                visualizations["platform_comparison"] = fig_bar.to_html(
                    include_plotlyjs="cdn",
                )

            # Engagement trend line (simulated data)
            dates = [
                (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(7, 0, -1)
            ]
            import random

            engagement_values = [random.uniform(2.0, 8.0) for _ in dates]

            fig_trend = go.Figure()
            fig_trend.add_trace(
                go.Scatter(
                    x=dates,
                    y=engagement_values,
                    mode="lines+markers",
                    name="Engagement Rate",
                    line=dict(color="#1f77b4", width=3),
                ),
            )
            fig_trend.update_layout(
                title="7-Day Engagement Trend",
                xaxis_title="Date",
                yaxis_title="Engagement Rate (%)",
            )
            visualizations["engagement_trend"] = fig_trend.to_html(
                include_plotlyjs="cdn",
            )

        except Exception as e:
            self.logger.error(f"Failed to create visualizations: {e}")
            visualizations["error"] = f"Visualization creation failed: {str(e)}"

        return visualizations

    async def _check_alert_conditions(self, metrics: dict) -> list[str]:
        """Check for alert conditions"""
        alerts = []

        # Low engagement alert
        avg_engagement = metrics["aggregated"].get("average_engagement_rate", 0)
        if avg_engagement < self.config["thresholds"]["low_engagement"]:
            alerts.append(
                f"🚨 LOW ENGAGEMENT: Average engagement rate is {
                    avg_engagement:.1f}% (threshold: {
                    self.config['thresholds']['low_engagement']
                }%)",
            )

        # High engagement celebration
        if avg_engagement > self.config["thresholds"]["high_engagement"]:
            alerts.append(
                f"🎉 HIGH ENGAGEMENT: Average engagement rate is {
                    avg_engagement:.1f}%!",
            )

        # Viral content detected
        viral_count = metrics["aggregated"].get("total_viral_content", 0)
        if viral_count > 0:
            alerts.append(
                f"🚀 VIRAL CONTENT: {viral_count} pieces of content went viral today!",
            )

        # Platform performance alerts
        platform_performance = metrics["aggregated"].get("platform_performance", {})
        for platform, perf in platform_performance.items():
            if perf["score"] < 30:
                alerts.append(
                    f"⚠️ {platform.upper()} UNDERPERFORMING: Score {
                        perf['score']:.1f}/100",
                )
            elif perf["score"] > 80:
                alerts.append(
                    f"⭐ {platform.upper()} EXCELLING: Score {perf['score']:.1f}/100",
                )

        # Store alerts in database
        await self._store_alerts(alerts)

        return alerts

    def _calculate_roi_analysis(self, metrics: dict) -> dict:
        """Calculate ROI analysis"""
        # This would integrate with actual cost and revenue data
        import random

        roi_analysis = {
            "total_spend": random.randint(1000, 5000),
            "total_revenue": random.randint(10000, 50000),
            "roi_percentage": 0,
            "cost_per_acquisition": random.randint(20, 100),
            "ltv_cac_ratio": round(random.uniform(2.5, 5.0), 1),
            "platform_roi": {},
            "content_type_roi": {},
        }

        # Calculate ROI
        if roi_analysis["total_spend"] > 0:
            roi_analysis["roi_percentage"] = (
                (roi_analysis["total_revenue"] - roi_analysis["total_spend"])
                / roi_analysis["total_spend"]
            ) * 100

        # Platform-specific ROI (simulated)
        for platform in metrics["platforms"].keys():
            if "error" not in metrics["platforms"][platform]:
                roi_analysis["platform_roi"][platform] = {
                    "spend": random.randint(200, 1000),
                    "revenue": random.randint(2000, 10000),
                    "roi": round(random.uniform(200, 800), 1),
                }

        return roi_analysis

    async def _store_alerts(self, alerts: list[str]):
        """Store alerts in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for alert in alerts:
            # Parse alert type and severity from message
            if "🚨" in alert:
                alert_type = "critical"
                severity = "high"
            elif "⚠️" in alert:
                alert_type = "warning"
                severity = "medium"
            elif "🎉" in alert or "🚀" in alert or "⭐" in alert:
                alert_type = "success"
                severity = "low"
            else:
                alert_type = "info"
                severity = "medium"

            cursor.execute(
                """
                INSERT INTO alerts (alert_type, severity, message, acknowledged)
                VALUES (?, ?, ?, FALSE)
            """,
                (alert_type, severity, alert),
            )

        conn.commit()
        conn.close()

    async def _store_report(self, report: PerformanceReport):
        """Store performance report in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO performance_reports (date, report_type, report_data)
            VALUES (?, ?, ?)
        """,
            (report.date, "daily", json.dumps(asdict(report), default=str)),
        )

        conn.commit()
        conn.close()

    async def _send_slack_report(self, report: PerformanceReport):
        """Send formatted report to Slack"""
        if "slack" not in self.clients:
            return

        try:
            # Format metrics for Slack
            top_metrics = self._format_top_metrics_for_slack(report)

            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📊 Daily Vibe Report - {report.date}",
                    },
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": report.executive_summary},
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*🚀 Top Metrics:*\n{top_metrics}",
                    },
                },
            ]

            # Add recommendations section
            if report.recommendations:
                recommendations_text = "\n".join(
                    [f"• {rec}" for rec in report.recommendations[:3]],
                )
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*💡 AI Recommendations:*\n{recommendations_text}",
                        },
                    },
                )

            # Add alerts section
            if report.alerts:
                alerts_text = "\n".join(report.alerts[:3])
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*🔔 Alerts:*\n{alerts_text}",
                        },
                    },
                )

            # Send to configured channel
            channel = self.config["channels"]["reports"]
            await self.clients["slack"].chat_postMessage(channel=channel, blocks=blocks)

            self.logger.info(f"Report sent to Slack channel {channel}")

        except Exception as e:
            self.logger.error(f"Failed to send Slack report: {e}")

    def _format_top_metrics_for_slack(self, report: PerformanceReport) -> str:
        """Format top metrics for Slack display"""
        content = report.content_performance
        social = report.social_growth

        metrics_text = []

        # Extract key metrics (with fallbacks for missing data)
        total_followers = sum(
            growth.get("current", 0)
            for growth in social.get("follower_growth", {}).values()
        )

        avg_engagement = content.get("platform_breakdown", {})
        avg_eng_rate = sum(
            p.get("engagement_rate", 0) for p in avg_engagement.values()
        ) / max(len(avg_engagement), 1)

        viral_count = sum(
            p.get("viral_content_count", 0)
            for p in content.get("platform_breakdown", {}).values()
        )

        metrics_text.extend(
            [
                f"👥 Total Followers: {total_followers:,}",
                f"📈 Avg Engagement: {avg_eng_rate:.1f}%",
                f"🚀 Viral Content: {viral_count}",
                f"💰 ROI: {report.roi_analysis.get('roi_percentage', 0):.1f}%",
            ],
        )

        return "\n".join(metrics_text)


# Usage and testing functions


async def main():
    """Main function for testing analytics engine"""

    # Initialize analytics engine
    engine = VibeAnalyticsEngine()

    # Generate daily report
    print("Generating daily performance report...")
    report = await engine.generate_daily_report()

    print("\n=== DAILY VIBE REPORT ===")
    print(f"Date: {report.date}")
    print("\nExecutive Summary:")
    print(report.executive_summary)

    print("\nRecommendations:")
    for i, rec in enumerate(report.recommendations, 1):
        print(f"{i}. {rec}")

    if report.alerts:
        print("\nAlerts:")
        for alert in report.alerts:
            print(f"  {alert}")

    print("\nROI Analysis:")
    roi = report.roi_analysis
    print(f"  Total ROI: {roi.get('roi_percentage', 0):.1f}%")
    print(f"  LTV/CAC Ratio: {roi.get('ltv_cac_ratio', 0):.1f}")

    print("\n=== Report Generated Successfully ===")


if __name__ == "__main__":
    asyncio.run(main())
