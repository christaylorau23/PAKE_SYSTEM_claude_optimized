#!/usr/bin/env python3
"""
Social Media Distribution Network - Master Integration
Complete social media automation and management system
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

# Import all social media components
try:
    from content_optimization_engine import ContentOptimizationEngine
    from instagram_enhanced import InstagramEnhanced, InstagramMedia
    from social_analytics_dashboard import SocialAnalyticsDashboard
    from social_distributor import SocialMediaDistributor, SocialPost
    from social_listening_system import SocialListeningSystem
    from social_scheduler_system import (
        PostStatus,
        ScheduledPost,
        ScheduleFrequency,
        SocialSchedulerSystem,
    )
    from tiktok_integration import TikTokIntegration, TikTokVideo
except ImportError as e:
    print(f"Some modules not available: {e}")
    print("Make sure all social media modules are in the same directory")


class SocialMediaMaster:
    """Master controller for the complete social media distribution network"""

    def __init__(self, config_path: str = None):
        """Initialize the master social media system"""
        self.logger = self._setup_logging()
        self.config = self._load_configuration(config_path)

        # Initialize all components
        self.distributor = SocialMediaDistributor(config_path)
        self.analytics = SocialAnalyticsDashboard()
        self.optimizer = ContentOptimizationEngine(self.config.get("openai_api_key"))
        self.scheduler = SocialSchedulerSystem()
        self.listener = SocialListeningSystem()

        # Enhanced platform integrations
        self.instagram_enhanced = None
        self.tiktok_enhanced = None
        self._initialize_enhanced_platforms()

        # System status
        self.is_running = False
        self.background_tasks = []

        self.logger.info("Social Media Master System initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        log_dir = Path("../logs")
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_dir / "social_media_master.log"),
                logging.StreamHandler(),
            ],
        )

        return logging.getLogger(__name__)

    def _load_configuration(self, config_path: str = None) -> dict:
        """Load system configuration"""
        default_config = {
            "platforms": {
                "twitter": {"enabled": True, "priority": 1},
                "instagram": {"enabled": True, "priority": 1},
                "linkedin": {"enabled": True, "priority": 2},
                "tiktok": {"enabled": False, "priority": 3},
                "reddit": {"enabled": True, "priority": 2},
            },
            "automation": {
                "auto_optimize_content": True,
                "auto_schedule_optimal_times": True,
                "enable_social_listening": True,
                "auto_respond_to_mentions": False,
            },
            "content_rules": {
                "min_engagement_rate": 2.0,
                "max_posts_per_day": 10,
                "avoid_duplicate_content_hours": 24,
            },
            "monitoring": {
                "keywords": ["automation", "AI", "productivity"],
                "competitors": [],
                "brand_mentions": [],
            },
        }

        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                user_config = json.load(f)
                # Merge configurations
                default_config.update(user_config)

        return default_config

    def _initialize_enhanced_platforms(self):
        """Initialize enhanced platform integrations"""
        # Instagram Enhanced
        instagram_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        instagram_business_id = os.getenv("INSTAGRAM_BUSINESS_ID")

        if instagram_token and instagram_business_id:
            self.instagram_enhanced = InstagramEnhanced(
                instagram_token,
                instagram_business_id,
            )
            self.logger.info("Instagram Enhanced initialized")

        # TikTok Enhanced
        tiktok_key = os.getenv("TIKTOK_CLIENT_KEY")
        tiktok_secret = os.getenv("TIKTOK_CLIENT_SECRET")
        tiktok_token = os.getenv("TIKTOK_ACCESS_TOKEN")

        if all([tiktok_key, tiktok_secret, tiktok_token]):
            self.tiktok_enhanced = TikTokIntegration(
                tiktok_key,
                tiktok_secret,
                tiktok_token,
            )
            self.logger.info("TikTok Enhanced initialized")

    async def start_system(self):
        """Start the complete social media automation system"""
        self.logger.info("Starting Social Media Master System...")

        if self.is_running:
            self.logger.warning("System is already running")
            return

        self.is_running = True

        # Start scheduler
        self.scheduler.start_scheduler()

        # Start background tasks
        if self.config["automation"]["enable_social_listening"]:
            listening_task = asyncio.create_task(
                self.listener.start_listening(duration_hours=24),
            )
            self.background_tasks.append(listening_task)

        # Start analytics collection
        analytics_task = asyncio.create_task(self._run_analytics_collection())
        self.background_tasks.append(analytics_task)

        # Start content monitoring
        monitoring_task = asyncio.create_task(self._run_content_monitoring())
        self.background_tasks.append(monitoring_task)

        self.logger.info("Social Media Master System started successfully")

    async def stop_system(self):
        """Stop the social media automation system"""
        self.logger.info("Stopping Social Media Master System...")

        self.is_running = False

        # Stop scheduler
        self.scheduler.stop_scheduler()

        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        self.background_tasks.clear()

        self.logger.info("Social Media Master System stopped")

    async def create_and_optimize_post(
        self,
        content: str,
        platforms: list[str] = None,
        media_files: list[str] = None,
        schedule_time: datetime = None,
        campaign_id: str = None,
    ) -> dict:
        """Create, optimize, and optionally schedule a social media post"""

        try:
            # Use all enabled platforms if none specified
            if not platforms:
                platforms = [
                    p
                    for p, config in self.config["platforms"].items()
                    if config["enabled"]
                ]

            # Optimize content
            if self.config["automation"]["auto_optimize_content"]:
                optimization = await self.optimizer.optimize_content(
                    content=content,
                    target_platforms=platforms,
                    content_category="general",
                )

                optimized_content = optimization.optimized_content
                recommended_hashtags = optimization.recommended_hashtags

                self.logger.info(
                    f"Content optimized. Score: {optimization.content_score}",
                )
            else:
                optimized_content = content
                recommended_hashtags = []

            # Create social post
            social_post = SocialPost(
                content=optimized_content,
                media_paths=media_files,
                platforms=platforms,
                hashtags=recommended_hashtags,
            )

            result = {
                "success": True,
                "optimized_content": optimized_content,
                "platforms": platforms,
                "hashtags": recommended_hashtags,
            }

            # Schedule or post immediately
            if schedule_time:
                # Schedule the post
                scheduled_post = ScheduledPost(
                    content=optimized_content,
                    platforms=platforms,
                    scheduled_time=schedule_time,
                    status=PostStatus.SCHEDULED,
                    media_files=media_files,
                    hashtags=recommended_hashtags,
                    campaign_id=campaign_id,
                )

                post_id = await self.scheduler.schedule_post(scheduled_post)
                result["scheduled"] = True
                result["post_id"] = post_id
                result["scheduled_time"] = schedule_time

                self.logger.info(
                    f"Post scheduled for {schedule_time} with ID: {post_id}",
                )

            else:
                # Post immediately
                posting_results = await self.distributor.post_to_all_platforms(
                    social_post,
                )
                result["posting_results"] = posting_results
                result["posted_immediately"] = True

                # Check for any failures
                failed_platforms = [
                    p for p, r in posting_results.items() if r.get("error")
                ]
                if failed_platforms:
                    result["partial_failure"] = True
                    result["failed_platforms"] = failed_platforms

                self.logger.info(f"Post published to {len(platforms)} platforms")

            return result

        except Exception as e:
            self.logger.error(f"Failed to create and optimize post: {e}")
            return {"success": False, "error": str(e)}

    async def post_instagram_reel(
        self,
        video_path: str,
        caption: str,
        cover_url: str = None,
    ) -> dict:
        """Post an Instagram Reel with enhanced features"""
        if not self.instagram_enhanced:
            return {"success": False, "error": "Instagram Enhanced not configured"}

        try:
            # Optimize caption for Instagram
            optimization = await self.optimizer.optimize_content(
                content=caption,
                target_platforms=["instagram"],
                content_category="general",
            )

            optimized_caption = optimization.optimized_content
            hashtags = " ".join(optimization.recommended_hashtags)
            final_caption = f"{optimized_caption}\n\n{hashtags}"

            # Post Reel
            result = await self.instagram_enhanced.post_reel(
                video_url=video_path,
                caption=final_caption,
                cover_url=cover_url,
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to post Instagram Reel: {e}")
            return {"success": False, "error": str(e)}

    async def post_tiktok_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
    ) -> dict:
        """Post a TikTok video with optimization"""
        if not self.tiktok_enhanced:
            return {"success": False, "error": "TikTok Enhanced not configured"}

        try:
            # Optimize title and description
            title_opt = await self.optimizer.optimize_content(
                content=title,
                target_platforms=["tiktok"],
                content_category="general",
            )

            hashtags = " ".join(title_opt.recommended_hashtags)
            optimized_description = (
                f"{description}\n\n{hashtags}" if description else hashtags
            )

            # Create TikTok video object
            tiktok_video = TikTokVideo(
                video_path=video_path,
                title=title_opt.optimized_content,
                description=optimized_description,
                hashtags=title_opt.recommended_hashtags,
            )

            # Upload video
            result = await self.tiktok_enhanced.upload_video(tiktok_video)

            return result

        except Exception as e:
            self.logger.error(f"Failed to post TikTok video: {e}")
            return {"success": False, "error": str(e)}

    async def get_comprehensive_analytics(self, days: int = 30) -> dict:
        """Get comprehensive analytics across all platforms"""
        try:
            # Collect metrics from all platforms
            all_metrics = await self.analytics.collect_all_metrics()

            # Generate comprehensive report
            report = self.analytics.generate_comprehensive_report(days)

            # Get listening insights
            listening_report = await self.listener.generate_listening_report(days)

            # Get scheduling analytics
            scheduling_analytics = await self.scheduler.get_posting_analytics(days)

            return {
                "platform_metrics": all_metrics,
                "performance_report": report,
                "social_listening": listening_report,
                "scheduling_stats": scheduling_analytics,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to generate comprehensive analytics: {e}")
            return {"error": str(e)}

    async def _run_analytics_collection(self):
        """Background task for analytics collection"""
        while self.is_running:
            try:
                await self.analytics.collect_all_metrics()
                self.logger.info("Analytics collection completed")

                # Wait 1 hour before next collection
                await asyncio.sleep(3600)

            except Exception as e:
                self.logger.error(f"Analytics collection error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _run_content_monitoring(self):
        """Background task for content monitoring and alerts"""
        while self.is_running:
            try:
                # Check for alerts
                alerts = await self.listener.get_alerts(acknowledged=False)

                for alert in alerts:
                    self.logger.warning(f"SOCIAL ALERT: {alert['content']}")

                    # Auto-acknowledge low severity alerts
                    if alert["severity"] == "low":
                        await self.listener.acknowledge_alert(alert["id"])

                # Wait 15 minutes before next check
                await asyncio.sleep(900)

            except Exception as e:
                self.logger.error(f"Content monitoring error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def get_system_status(self) -> dict:
        """Get complete system status"""
        try:
            # Get pending posts
            pending_posts = await self.scheduler.get_scheduled_posts(
                status=PostStatus.SCHEDULED,
                limit=10,
            )

            # Get recent alerts
            alerts = await self.listener.get_alerts(acknowledged=False, limit=5)

            # Get analytics summary
            analytics_summary = await self.scheduler.get_posting_analytics(days=7)

            return {
                "system_running": self.is_running,
                "active_platforms": list(self.config["platforms"].keys()),
                "pending_posts": len(pending_posts),
                "unacknowledged_alerts": len(alerts),
                "weekly_posts": analytics_summary.get("total_posts", 0),
                "success_rate": analytics_summary.get("success_rate", 0),
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}")
            return {"error": str(e)}

    async def bulk_schedule_posts(self, posts_data: list[dict]) -> dict:
        """Schedule multiple posts in bulk"""
        results = {"successful": 0, "failed": 0, "post_ids": [], "errors": []}

        for post_data in posts_data:
            try:
                result = await self.create_and_optimize_post(
                    content=post_data["content"],
                    platforms=post_data.get("platforms"),
                    media_files=post_data.get("media_files"),
                    schedule_time=datetime.fromisoformat(post_data["schedule_time"]),
                    campaign_id=post_data.get("campaign_id"),
                )

                if result["success"]:
                    results["successful"] += 1
                    results["post_ids"].append(result["post_id"])
                else:
                    results["failed"] += 1
                    results["errors"].append(result["error"])

            except Exception as e:
                results["failed"] += 1
                results["errors"].append(str(e))

        self.logger.info(
            f"Bulk scheduling completed: {results['successful']} successful, {
                results['failed']
            } failed",
        )
        return results


# CLI Interface for easy usage


async def main():
    """Main CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="Social Media Distribution Network")
    parser.add_argument(
        "command",
        choices=["start", "post", "schedule", "analytics", "status"],
    )
    parser.add_argument("--content", help="Content to post")
    parser.add_argument("--platforms", nargs="+", help="Target platforms")
    parser.add_argument("--schedule-time", help="Schedule time (ISO format)")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--days", type=int, default=7, help="Days for analytics")

    args = parser.parse_args()

    # Initialize master system
    master = SocialMediaMaster(args.config)

    try:
        if args.command == "start":
            print("Starting Social Media Master System...")
            await master.start_system()

            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(60)
                    status = await master.get_system_status()
                    print(f"System Status: {status}")
            except KeyboardInterrupt:
                print("Stopping system...")
                await master.stop_system()

        elif args.command == "post":
            if not args.content:
                print("Error: --content is required for posting")
                return

            result = await master.create_and_optimize_post(
                content=args.content,
                platforms=args.platforms,
            )
            print(f"Post Result: {json.dumps(result, indent=2, default=str)}")

        elif args.command == "schedule":
            if not args.content or not args.schedule_time:
                print(
                    "Error: --content and --schedule-time are required for scheduling",
                )
                return

            schedule_time = datetime.fromisoformat(args.schedule_time)
            result = await master.create_and_optimize_post(
                content=args.content,
                platforms=args.platforms,
                schedule_time=schedule_time,
            )
            print(f"Schedule Result: {json.dumps(result, indent=2, default=str)}")

        elif args.command == "analytics":
            analytics = await master.get_comprehensive_analytics(args.days)
            print(f"Analytics Report: {json.dumps(analytics, indent=2, default=str)}")

        elif args.command == "status":
            status = await master.get_system_status()
            print(f"System Status: {json.dumps(status, indent=2, default=str)}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
