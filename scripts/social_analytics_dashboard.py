#!/usr/bin/env python3
"""
Social Media Analytics Dashboard
Comprehensive analytics and insights across all social platforms
"""

import json
import logging
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

# Data visualization and analytics
try:
    import matplotlib.pyplot as plt
    import pandas as pd
    import plotly.express as px
    import seaborn as sns
    from plotly import graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    print(
        "Analytics dependencies not installed. Run: pip install pandas matplotlib seaborn plotly",
    )


@dataclass
class SocialMetrics:
    """Social media metrics data structure"""

    platform: str
    post_id: str
    timestamp: datetime
    content_type: str  # text, image, video, reel, story
    engagement_rate: float = 0.0
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    clicks: int = 0
    views: int = 0  # for video content
    completion_rate: float = 0.0  # video completion rate
    hashtags: list[str] = None
    mentions: list[str] = None
    sentiment_score: float = 0.0
    optimal_time_posted: bool = False


@dataclass
class PlatformInsights:
    """Platform-specific insights"""

    platform: str
    total_posts: int
    avg_engagement_rate: float
    best_posting_times: list[str]
    top_content_types: list[str]
    trending_hashtags: list[str]
    audience_demographics: dict
    growth_rate: float
    roi_metrics: dict


class SocialAnalyticsDashboard:
    """Comprehensive social media analytics dashboard"""

    def __init__(self, db_path: str = "social_analytics.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()

        # Platform integrations
        self.platforms = {
            "twitter": None,
            "instagram": None,
            "tiktok": None,
            "reddit": None,
            "linkedin": None,
        }

    def _init_database(self):
        """Initialize SQLite database for analytics storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS social_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                post_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                content_type TEXT,
                engagement_rate REAL,
                impressions INTEGER,
                reach INTEGER,
                likes INTEGER,
                comments INTEGER,
                shares INTEGER,
                saves INTEGER,
                clicks INTEGER,
                views INTEGER,
                completion_rate REAL,
                hashtags TEXT,
                mentions TEXT,
                sentiment_score REAL,
                optimal_time_posted BOOLEAN,
                raw_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                date DATE NOT NULL,
                total_posts INTEGER,
                avg_engagement_rate REAL,
                best_posting_times TEXT,
                top_content_types TEXT,
                trending_hashtags TEXT,
                audience_demographics TEXT,
                growth_rate REAL,
                roi_metrics TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS content_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                post_id TEXT NOT NULL,
                content_hash TEXT,
                performance_score REAL,
                best_time_to_post TEXT,
                recommended_hashtags TEXT,
                audience_engagement TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        conn.commit()
        conn.close()

    async def collect_all_metrics(self) -> dict:
        """Collect metrics from all configured platforms"""
        all_metrics = {}

        for platform_name, client in self.platforms.items():
            if client:
                try:
                    metrics = await self._collect_platform_metrics(
                        platform_name,
                        client,
                    )
                    all_metrics[platform_name] = metrics

                    # Store metrics in database
                    await self._store_metrics(metrics)

                except Exception as e:
                    self.logger.error(
                        f"Failed to collect metrics for {platform_name}: {e}",
                    )
                    all_metrics[platform_name] = {"error": str(e)}

        return all_metrics

    async def _collect_platform_metrics(
        self,
        platform: str,
        client,
    ) -> list[SocialMetrics]:
        """Collect metrics from a specific platform"""
        metrics = []

        if platform == "twitter":
            metrics = await self._collect_twitter_metrics(client)
        elif platform == "instagram":
            metrics = await self._collect_instagram_metrics(client)
        elif platform == "tiktok":
            metrics = await self._collect_tiktok_metrics(client)
        elif platform == "reddit":
            metrics = await self._collect_reddit_metrics(client)
        elif platform == "linkedin":
            metrics = await self._collect_linkedin_metrics(client)

        return metrics

    async def _collect_twitter_metrics(self, client) -> list[SocialMetrics]:
        """Collect Twitter/X metrics"""
        metrics = []

        try:
            # Get recent tweets
            tweets = client.get_users_tweets(
                client.get_me().data.id,
                max_results=100,
                tweet_fields=["created_at", "public_metrics", "context_annotations"],
            )

            for tweet in tweets.data or []:
                metrics.append(
                    SocialMetrics(
                        platform="twitter",
                        post_id=tweet.id,
                        timestamp=tweet.created_at,
                        content_type="text",
                        likes=tweet.public_metrics.get("like_count", 0),
                        comments=tweet.public_metrics.get("reply_count", 0),
                        shares=tweet.public_metrics.get("retweet_count", 0),
                        impressions=tweet.public_metrics.get("impression_count", 0),
                        engagement_rate=self._calculate_engagement_rate(
                            tweet.public_metrics.get("like_count", 0)
                            + tweet.public_metrics.get("reply_count", 0)
                            + tweet.public_metrics.get("retweet_count", 0),
                            tweet.public_metrics.get("impression_count", 1),
                        ),
                    ),
                )

        except Exception as e:
            self.logger.error(f"Twitter metrics collection failed: {e}")

        return metrics

    async def _collect_instagram_metrics(self, client) -> list[SocialMetrics]:
        """Collect Instagram metrics"""
        metrics = []

        try:
            # This would use Instagram Graph API
            # Implementation depends on your Instagram client setup
            pass

        except Exception as e:
            self.logger.error(f"Instagram metrics collection failed: {e}")

        return metrics

    async def _collect_tiktok_metrics(self, client) -> list[SocialMetrics]:
        """Collect TikTok metrics"""
        metrics = []

        try:
            # Get video list with analytics
            video_response = await client.get_video_list()

            if video_response.get("success"):
                for video in video_response["videos"]:
                    # Get detailed analytics for each video
                    analytics = await client.get_video_analytics(video["id"])

                    if analytics.get("success"):
                        analytics_data = analytics["analytics"]

                        metrics.append(
                            SocialMetrics(
                                platform="tiktok",
                                post_id=video["id"],
                                timestamp=datetime.fromtimestamp(
                                    video.get("create_time", 0),
                                ),
                                content_type="video",
                                views=analytics_data.get("views", 0),
                                likes=analytics_data.get("likes", 0),
                                comments=analytics_data.get("comments", 0),
                                shares=analytics_data.get("shares", 0),
                                reach=analytics_data.get("reach", 0),
                                engagement_rate=self._calculate_engagement_rate(
                                    analytics_data.get("likes", 0)
                                    + analytics_data.get("comments", 0)
                                    + analytics_data.get("shares", 0),
                                    analytics_data.get("views", 1),
                                ),
                            ),
                        )

        except Exception as e:
            self.logger.error(f"TikTok metrics collection failed: {e}")

        return metrics

    async def _collect_reddit_metrics(self, client) -> list[SocialMetrics]:
        """Collect Reddit metrics"""
        metrics = []

        try:
            # Get user's recent submissions
            for submission in client.user.me().submissions.new(limit=100):
                metrics.append(
                    SocialMetrics(
                        platform="reddit",
                        post_id=submission.id,
                        timestamp=datetime.fromtimestamp(submission.created_utc),
                        content_type="text" if submission.is_self else "link",
                        likes=submission.score,
                        comments=submission.num_comments,
                        engagement_rate=self._calculate_engagement_rate(
                            submission.score + submission.num_comments,
                            max(submission.view_count or 0, 1),
                        ),
                    ),
                )

        except Exception as e:
            self.logger.error(f"Reddit metrics collection failed: {e}")

        return metrics

    async def _collect_linkedin_metrics(self, client) -> list[SocialMetrics]:
        """Collect LinkedIn metrics"""
        metrics = []

        try:
            # LinkedIn API implementation would go here
            pass

        except Exception as e:
            self.logger.error(f"LinkedIn metrics collection failed: {e}")

        return metrics

    def _calculate_engagement_rate(
        self,
        total_engagement: int,
        impressions: int,
    ) -> float:
        """Calculate engagement rate"""
        if impressions == 0:
            return 0.0
        return (total_engagement / impressions) * 100

    async def _store_metrics(self, metrics: list[SocialMetrics]):
        """Store metrics in database"""
        if not metrics:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for metric in metrics:
            cursor.execute(
                """
                INSERT OR REPLACE INTO social_metrics
                (platform, post_id, timestamp, content_type, engagement_rate,
                 impressions, reach, likes, comments, shares, saves, clicks,
                 views, completion_rate, hashtags, mentions, sentiment_score,
                 optimal_time_posted, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    metric.platform,
                    metric.post_id,
                    metric.timestamp,
                    metric.content_type,
                    metric.engagement_rate,
                    metric.impressions,
                    metric.reach,
                    metric.likes,
                    metric.comments,
                    metric.shares,
                    metric.saves,
                    metric.clicks,
                    metric.views,
                    metric.completion_rate,
                    json.dumps(metric.hashtags) if metric.hashtags else None,
                    json.dumps(metric.mentions) if metric.mentions else None,
                    metric.sentiment_score,
                    metric.optimal_time_posted,
                    json.dumps(asdict(metric)),
                ),
            )

        conn.commit()
        conn.close()

    def generate_comprehensive_report(self, days: int = 30) -> dict:
        """Generate comprehensive analytics report"""
        conn = sqlite3.connect(self.db_path)

        # Date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        query = """
            SELECT * FROM social_metrics
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp DESC
        """

        df = pd.read_sql_query(query, conn, params=[start_date, end_date])
        conn.close()

        if df.empty:
            return {"error": "No data available for the specified period"}

        # Generate insights
        report = {
            "summary": self._generate_summary(df),
            "platform_comparison": self._compare_platforms(df),
            "content_analysis": self._analyze_content_performance(df),
            "engagement_trends": self._analyze_engagement_trends(df),
            "optimal_posting_times": self._find_optimal_posting_times(df),
            "recommendations": self._generate_recommendations(df),
        }

        return report

    def _generate_summary(self, df: pd.DataFrame) -> dict:
        """Generate summary statistics"""
        return {
            "total_posts": len(df),
            "total_platforms": df["platform"].nunique(),
            "avg_engagement_rate": df["engagement_rate"].mean(),
            "total_likes": df["likes"].sum(),
            "total_comments": df["comments"].sum(),
            "total_shares": df["shares"].sum(),
            "total_views": df["views"].sum(),
            "best_performing_platform": df.groupby("platform")["engagement_rate"]
            .mean()
            .idxmax(),
            "date_range": {
                "start": df["timestamp"].min(),
                "end": df["timestamp"].max(),
            },
        }

    def _compare_platforms(self, df: pd.DataFrame) -> dict:
        """Compare performance across platforms"""
        platform_stats = (
            df.groupby("platform")
            .agg(
                {
                    "engagement_rate": ["mean", "median", "std"],
                    "likes": "sum",
                    "comments": "sum",
                    "shares": "sum",
                    "views": "sum",
                },
            )
            .round(2)
        )

        return platform_stats.to_dict()

    def _analyze_content_performance(self, df: pd.DataFrame) -> dict:
        """Analyze content performance by type"""
        content_analysis = (
            df.groupby("content_type")
            .agg(
                {
                    "engagement_rate": "mean",
                    "likes": "mean",
                    "comments": "mean",
                    "shares": "mean",
                    "views": "mean",
                },
            )
            .round(2)
        )

        return {
            "by_content_type": content_analysis.to_dict(),
            "best_content_type": content_analysis["engagement_rate"].idxmax(),
        }

    def _analyze_engagement_trends(self, df: pd.DataFrame) -> dict:
        """Analyze engagement trends over time"""
        df["date"] = pd.to_datetime(df["timestamp"]).dt.date
        daily_engagement = df.groupby("date")["engagement_rate"].mean().to_dict()

        # Convert date objects to strings for JSON serialization
        daily_engagement = {str(k): v for k, v in daily_engagement.items()}

        return {
            "daily_engagement": daily_engagement,
            "trend_direction": self._calculate_trend(list(daily_engagement.values())),
        }

    def _find_optimal_posting_times(self, df: pd.DataFrame) -> dict:
        """Find optimal posting times by platform"""
        df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour
        df["day_of_week"] = pd.to_datetime(df["timestamp"]).dt.day_name()

        optimal_times = {}
        for platform in df["platform"].unique():
            platform_df = df[df["platform"] == platform]

            best_hours = (
                platform_df.groupby("hour")["engagement_rate"]
                .mean()
                .nlargest(3)
                .index.tolist()
            )
            best_days = (
                platform_df.groupby("day_of_week")["engagement_rate"]
                .mean()
                .nlargest(3)
                .index.tolist()
            )

            optimal_times[platform] = {
                "best_hours": [f"{hour:02d}:00" for hour in best_hours],
                "best_days": best_days,
            }

        return optimal_times

    def _calculate_trend(self, values: list[float]) -> str:
        """Calculate trend direction"""
        if len(values) < 2:
            return "insufficient_data"

        # Simple linear regression slope
        x = list(range(len(values)))
        slope = sum(
            (x[i] - sum(x) / len(x)) * (values[i] - sum(values) / len(values))
            for i in range(len(values))
        ) / sum((x[i] - sum(x) / len(x)) ** 2 for i in range(len(x)))

        if slope > 0.1:
            return "increasing"
        if slope < -0.1:
            return "decreasing"
        return "stable"

    def _generate_recommendations(self, df: pd.DataFrame) -> list[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Engagement rate recommendations
        avg_engagement = df["engagement_rate"].mean()
        if avg_engagement < 2.0:
            recommendations.append(
                "Consider improving content quality to increase engagement rates",
            )

        # Platform-specific recommendations
        platform_performance = df.groupby("platform")["engagement_rate"].mean()
        best_platform = platform_performance.idxmax()
        worst_platform = platform_performance.idxmin()

        recommendations.append(
            f"Focus more efforts on {best_platform} which shows highest engagement",
        )
        recommendations.append(
            f"Review strategy for {worst_platform} to improve performance",
        )

        # Content type recommendations
        content_performance = df.groupby("content_type")["engagement_rate"].mean()
        if not content_performance.empty:
            best_content = content_performance.idxmax()
            recommendations.append(
                f"Create more {best_content} content as it performs best",
            )

        # Posting time recommendations
        df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour
        best_hour = df.groupby("hour")["engagement_rate"].mean().idxmax()
        recommendations.append(
            f"Post more content around {best_hour:02d}:00 for better engagement",
        )

        return recommendations

    def create_visualizations(self, days: int = 30) -> dict[str, str]:
        """Create visualization charts and return file paths"""
        report = self.generate_comprehensive_report(days)

        if "error" in report:
            return report

        viz_paths = {}

        # Create visualizations directory
        viz_dir = Path("../data/visualizations")
        viz_dir.mkdir(exist_ok=True)

        try:
            # Platform comparison chart
            platform_data = report["platform_comparison"]
            if platform_data:
                fig = self._create_platform_comparison_chart(platform_data)
                path = viz_dir / "platform_comparison.html"
                fig.write_html(str(path))
                viz_paths["platform_comparison"] = str(path)

            # Engagement trends chart
            trends_data = report["engagement_trends"]["daily_engagement"]
            if trends_data:
                fig = self._create_engagement_trends_chart(trends_data)
                path = viz_dir / "engagement_trends.html"
                fig.write_html(str(path))
                viz_paths["engagement_trends"] = str(path)

            # Content performance chart
            content_data = report["content_analysis"]
            if content_data:
                fig = self._create_content_performance_chart(content_data)
                path = viz_dir / "content_performance.html"
                fig.write_html(str(path))
                viz_paths["content_performance"] = str(path)

        except Exception as e:
            self.logger.error(f"Visualization creation failed: {e}")
            viz_paths["error"] = str(e)

        return viz_paths

    def _create_platform_comparison_chart(self, data: dict) -> go.Figure:
        """Create platform comparison chart"""
        platforms = list(data.keys()) if data else []

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=[
                "Engagement Rate",
                "Total Likes",
                "Total Comments",
                "Total Shares",
            ],
        )

        # Add traces for each metric
        metrics = ["engagement_rate", "likes", "comments", "shares"]
        positions = [(1, 1), (1, 2), (2, 1), (2, 2)]

        for i, metric in enumerate(metrics):
            row, col = positions[i]
            values = [
                (
                    data.get(platform, {}).get(metric, {}).get("sum", 0)
                    if metric != "engagement_rate"
                    else data.get(platform, {}).get(metric, {}).get("mean", 0)
                )
                for platform in platforms
            ]

            fig.add_trace(
                go.Bar(x=platforms, y=values, name=metric.title()),
                row=row,
                col=col,
            )

        fig.update_layout(
            height=600,
            showlegend=False,
            title_text="Platform Performance Comparison",
        )
        return fig

    def _create_engagement_trends_chart(self, data: dict) -> go.Figure:
        """Create engagement trends chart"""
        dates = list(data.keys())
        values = list(data.values())

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=values,
                mode="lines+markers",
                name="Engagement Rate",
                line=dict(color="#1f77b4", width=2),
            ),
        )

        fig.update_layout(
            title="Engagement Trends Over Time",
            xaxis_title="Date",
            yaxis_title="Engagement Rate (%)",
            height=400,
        )

        return fig

    def _create_content_performance_chart(self, data: dict) -> go.Figure:
        """Create content performance chart"""
        content_data = data.get("by_content_type", {})

        if not content_data:
            return go.Figure().add_annotation(text="No data available")

        content_types = list(content_data.get("engagement_rate", {}).keys())
        engagement_rates = list(content_data.get("engagement_rate", {}).values())

        fig = go.Figure(
            data=[
                go.Bar(
                    x=content_types,
                    y=engagement_rates,
                    marker_color="lightblue",
                    name="Engagement Rate",
                ),
            ],
        )

        fig.update_layout(
            title="Content Performance by Type",
            xaxis_title="Content Type",
            yaxis_title="Average Engagement Rate (%)",
            height=400,
        )

        return fig

    def export_report(self, format_type: str = "json", days: int = 30) -> str:
        """Export analytics report in various formats"""
        report = self.generate_comprehensive_report(days)

        if "error" in report:
            return report

        export_dir = Path("../data/reports")
        export_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format_type == "json":
            filename = f"social_analytics_report_{timestamp}.json"
            filepath = export_dir / filename

            # Convert datetime objects to strings for JSON serialization
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object {obj} is not JSON serializable")

            with open(filepath, "w") as f:
                json.dump(report, f, indent=2, default=serialize_datetime)

        elif format_type == "csv":
            filename = f"social_analytics_data_{timestamp}.csv"
            filepath = export_dir / filename

            # Export raw data as CSV
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(
                "SELECT * FROM social_metrics ORDER BY timestamp DESC",
                conn,
            )
            df.to_csv(filepath, index=False)
            conn.close()

        return str(filepath)


def main():
    """Main function for testing analytics dashboard"""
    dashboard = SocialAnalyticsDashboard()

    # Generate sample report
    report = dashboard.generate_comprehensive_report(days=30)
    print("Analytics Report Generated:")
    print(json.dumps(report, indent=2, default=str))

    # Create visualizations
    viz_paths = dashboard.create_visualizations(days=30)
    print(f"\nVisualizations created: {viz_paths}")

    # Export report
    export_path = dashboard.export_report("json", days=30)
    print(f"Report exported to: {export_path}")


if __name__ == "__main__":
    main()
