#!/usr/bin/env python3
"""
Advanced Social Media Scheduling System
Intelligent scheduling with optimal timing and content queue management
"""

import asyncio
import json
import logging
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum

import pytz

# Job scheduling
try:
    import croniter
    import schedule
    from apscheduler.executors.pool import ThreadPoolExecutor
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
except ImportError:
    print(
        "Scheduler dependencies not installed. Run: pip install schedule croniter apscheduler",
    )


class PostStatus(Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    POSTED = "posted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduleFrequency(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


@dataclass
class ScheduledPost:
    """Scheduled social media post"""

    id: str
    content: str
    platforms: list[str]
    scheduled_time: datetime
    status: PostStatus
    media_files: list[str] = None
    hashtags: list[str] = None
    mentions: list[str] = None
    timezone: str = "UTC"
    recurring: bool = False
    frequency: ScheduleFrequency = ScheduleFrequency.ONCE
    cron_expression: str = None
    max_retries: int = 3
    retry_count: int = 0
    priority: int = 1  # 1=high, 2=medium, 3=low
    campaign_id: str = None
    created_at: datetime = None
    updated_at: datetime = None
    posted_at: datetime = None
    error_message: str = None
    engagement_tracking: bool = True


@dataclass
class PostingSchedule:
    """Platform-specific posting schedule"""

    platform: str
    optimal_times: list[str]
    timezone: str
    frequency_limits: dict[str, int]  # max posts per hour/day
    blackout_periods: list[tuple[str, str]] = None  # periods to avoid posting


class SocialSchedulerSystem:
    """Advanced social media scheduling system"""

    def __init__(self, db_path: str = "scheduler.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

        # Initialize database
        self._init_database()

        # Initialize APScheduler
        jobstores = {"default": SQLAlchemyJobStore(url=f"sqlite:///{db_path}")}
        executors = {"default": ThreadPoolExecutor(20)}
        job_defaults = {"coalesce": False, "max_instances": 3}

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.UTC,
        )

        # Platform-specific schedules
        self.platform_schedules = self._load_platform_schedules()

        # Rate limiting
        self.rate_limits = {
            "twitter": {"hour": 300, "day": 2400},
            "instagram": {"hour": 25, "day": 200},
            "linkedin": {"hour": 20, "day": 100},
            "tiktok": {"hour": 10, "day": 50},
            "reddit": {"hour": 60, "day": 500},
        }

        # Posting counters
        self.posting_counters = {}

    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                platforms TEXT NOT NULL,
                scheduled_time DATETIME NOT NULL,
                status TEXT NOT NULL,
                media_files TEXT,
                hashtags TEXT,
                mentions TEXT,
                timezone TEXT DEFAULT 'UTC',
                recurring BOOLEAN DEFAULT FALSE,
                frequency TEXT,
                cron_expression TEXT,
                max_retries INTEGER DEFAULT 3,
                retry_count INTEGER DEFAULT 0,
                priority INTEGER DEFAULT 1,
                campaign_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                posted_at DATETIME,
                error_message TEXT,
                engagement_tracking BOOLEAN DEFAULT TRUE,
                raw_data TEXT
            )
        """,
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS posting_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                posted_time DATETIME NOT NULL,
                engagement_rate REAL,
                impressions INTEGER,
                likes INTEGER,
                comments INTEGER,
                shares INTEGER,
                clicks INTEGER,
                cost REAL,
                revenue REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES scheduled_posts (id)
            )
        """,
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS posting_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                scheduled_time DATETIME NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES scheduled_posts (id)
            )
        """,
        )

        conn.commit()
        conn.close()

    def _load_platform_schedules(self) -> dict[str, PostingSchedule]:
        """Load platform-specific optimal posting schedules"""
        return {
            "twitter": PostingSchedule(
                platform="twitter",
                optimal_times=["09:00", "12:00", "15:00", "18:00", "21:00"],
                timezone="UTC",
                frequency_limits={"hour": 50, "day": 400},
                blackout_periods=[("02:00", "06:00")],  # Low engagement hours
            ),
            "instagram": PostingSchedule(
                platform="instagram",
                optimal_times=["11:00", "14:00", "17:00", "20:00"],
                timezone="UTC",
                frequency_limits={"hour": 4, "day": 25},
            ),
            "linkedin": PostingSchedule(
                platform="linkedin",
                optimal_times=["08:00", "12:00", "17:00", "18:00"],
                timezone="UTC",
                frequency_limits={"hour": 5, "day": 20},
                blackout_periods=[
                    ("22:00", "06:00"),
                    ("12:00", "13:00"),
                ],  # Off-work hours
            ),
            "tiktok": PostingSchedule(
                platform="tiktok",
                optimal_times=["06:00", "10:00", "16:00", "19:00", "22:00"],
                timezone="UTC",
                frequency_limits={"hour": 3, "day": 10},
            ),
            "reddit": PostingSchedule(
                platform="reddit",
                optimal_times=["08:00", "12:00", "17:00", "21:00"],
                timezone="UTC",
                frequency_limits={"hour": 10, "day": 50},
            ),
        }

    async def schedule_post(self, post: ScheduledPost) -> str:
        """Schedule a post for publication"""
        try:
            # Generate unique ID if not provided
            if not post.id:
                post.id = str(uuid.uuid4())

            # Set creation time
            post.created_at = datetime.now(UTC)
            post.updated_at = post.created_at

            # Optimize scheduling time if not specified
            if not post.scheduled_time:
                post.scheduled_time = await self._find_optimal_posting_time(
                    post.platforms[0],
                )

            # Validate scheduling constraints
            validation_result = await self._validate_post_scheduling(post)
            if not validation_result["valid"]:
                raise ValueError(validation_result["error"])

            # Store in database
            await self._store_scheduled_post(post)

            # Add to scheduler
            if post.recurring:
                await self._schedule_recurring_post(post)
            else:
                await self._schedule_single_post(post)

            self.logger.info(f"Post {post.id} scheduled for {post.scheduled_time}")
            return post.id

        except Exception as e:
            self.logger.error(f"Failed to schedule post: {e}")
            raise

    async def _find_optimal_posting_time(
        self,
        platform: str,
        target_timezone: str = "UTC",
    ) -> datetime:
        """Find the next optimal posting time for a platform"""
        schedule_config = self.platform_schedules.get(platform)
        if not schedule_config:
            # Default to next hour if no config
            return datetime.now(UTC) + timedelta(hours=1)

        now = datetime.now(pytz.timezone(target_timezone))
        optimal_times = schedule_config.optimal_times

        # Find next optimal time today
        for time_str in optimal_times:
            hour, minute = map(int, time_str.split(":"))
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if target_time > now:
                # Check if this time is in blackout period
                if not self._is_blackout_time(target_time, schedule_config):
                    return target_time.astimezone(UTC)

        # No optimal time today, use first optimal time tomorrow
        tomorrow = now + timedelta(days=1)
        hour, minute = map(int, optimal_times[0].split(":"))
        target_time = tomorrow.replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )

        return target_time.astimezone(UTC)

    def _is_blackout_time(
        self,
        target_time: datetime,
        schedule_config: PostingSchedule,
    ) -> bool:
        """Check if target time is during a blackout period"""
        if not schedule_config.blackout_periods:
            return False

        current_time_str = target_time.strftime("%H:%M")

        for start_time, end_time in schedule_config.blackout_periods:
            if start_time <= current_time_str <= end_time:
                return True

        return False

    async def _validate_post_scheduling(self, post: ScheduledPost) -> dict:
        """Validate post scheduling constraints"""
        try:
            # Check if platforms are supported
            supported_platforms = list(self.platform_schedules.keys())
            invalid_platforms = [
                p for p in post.platforms if p not in supported_platforms
            ]
            if invalid_platforms:
                return {
                    "valid": False,
                    "error": f"Unsupported platforms: {invalid_platforms}",
                }

            # Check rate limits
            for platform in post.platforms:
                if not await self._check_rate_limits(platform, post.scheduled_time):
                    return {
                        "valid": False,
                        "error": f"Rate limit exceeded for {platform}",
                    }

            # Check content length limits
            for platform in post.platforms:
                max_length = {
                    "twitter": 280,
                    "instagram": 2200,
                    "linkedin": 3000,
                    "tiktok": 150,
                    "reddit": 40000,
                }.get(platform, 1000)
                if len(post.content) > max_length:
                    return {
                        "valid": False,
                        "error": f"Content too long for {platform} (max: {max_length})",
                    }

            # Check scheduling time is in future
            if post.scheduled_time <= datetime.now(UTC):
                return {"valid": False, "error": "Scheduled time must be in the future"}

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def _check_rate_limits(self, platform: str, scheduled_time: datetime) -> bool:
        """Check if posting at scheduled time would exceed rate limits"""
        limits = self.rate_limits.get(platform, {})

        # Check hourly limit
        hour_start = scheduled_time.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)

        hourly_posts = await self._count_posts_in_timeframe(
            platform,
            hour_start,
            hour_end,
        )

        if hourly_posts >= limits.get("hour", 100):
            return False

        # Check daily limit
        day_start = scheduled_time.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        daily_posts = await self._count_posts_in_timeframe(platform, day_start, day_end)

        if daily_posts >= limits.get("day", 1000):
            return False

        return True

    async def _count_posts_in_timeframe(
        self,
        platform: str,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        """Count scheduled posts for platform in timeframe"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT COUNT(*) FROM scheduled_posts
            WHERE platforms LIKE ?
            AND scheduled_time >= ?
            AND scheduled_time < ?
            AND status NOT IN ('cancelled', 'failed')
        """

        # Use parameterized query to prevent SQL injection
        platform_pattern = f"%{platform}%"
        cursor.execute(query, (platform_pattern, start_time, end_time))
        count = cursor.fetchone()[0]

        conn.close()
        return count

    async def _store_scheduled_post(self, post: ScheduledPost):
        """Store scheduled post in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO scheduled_posts (
                id, content, platforms, scheduled_time, status, media_files,
                hashtags, mentions, timezone, recurring, frequency, cron_expression,
                max_retries, retry_count, priority, campaign_id, created_at,
                updated_at, error_message, engagement_tracking, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                post.id,
                post.content,
                json.dumps(post.platforms),
                post.scheduled_time,
                post.status.value,
                json.dumps(post.media_files) if post.media_files else None,
                json.dumps(post.hashtags) if post.hashtags else None,
                json.dumps(post.mentions) if post.mentions else None,
                post.timezone,
                post.recurring,
                post.frequency.value if post.frequency else None,
                post.cron_expression,
                post.max_retries,
                post.retry_count,
                post.priority,
                post.campaign_id,
                post.created_at,
                post.updated_at,
                post.error_message,
                post.engagement_tracking,
                json.dumps(asdict(post)),
            ),
        )

        conn.commit()
        conn.close()

    async def _schedule_single_post(self, post: ScheduledPost):
        """Schedule a single post using APScheduler"""
        self.scheduler.add_job(
            func=self._execute_post,
            trigger="date",
            run_date=post.scheduled_time,
            args=[post.id],
            id=post.id,
            replace_existing=True,
            misfire_grace_time=300,  # 5 minutes grace period
        )

    async def _schedule_recurring_post(self, post: ScheduledPost):
        """Schedule a recurring post"""
        if post.frequency == ScheduleFrequency.DAILY:
            self.scheduler.add_job(
                func=self._execute_post,
                trigger="interval",
                days=1,
                start_date=post.scheduled_time,
                args=[post.id],
                id=post.id,
                replace_existing=True,
            )
        elif post.frequency == ScheduleFrequency.WEEKLY:
            self.scheduler.add_job(
                func=self._execute_post,
                trigger="interval",
                weeks=1,
                start_date=post.scheduled_time,
                args=[post.id],
                id=post.id,
                replace_existing=True,
            )
        elif post.frequency == ScheduleFrequency.MONTHLY:
            self.scheduler.add_job(
                func=self._execute_post,
                trigger="interval",
                days=30,
                start_date=post.scheduled_time,
                args=[post.id],
                id=post.id,
                replace_existing=True,
            )
        elif post.frequency == ScheduleFrequency.CUSTOM and post.cron_expression:
            self.scheduler.add_job(
                func=self._execute_post,
                trigger="cron",
                **self._parse_cron_expression(post.cron_expression),
                args=[post.id],
                id=post.id,
                replace_existing=True,
            )

    def _parse_cron_expression(self, cron_expr: str) -> dict:
        """Parse cron expression for APScheduler"""
        # Basic cron parsing - in production use croniter
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError("Invalid cron expression")

        return {
            "minute": parts[0] if parts[0] != "*" else None,
            "hour": parts[1] if parts[1] != "*" else None,
            "day": parts[2] if parts[2] != "*" else None,
            "month": parts[3] if parts[3] != "*" else None,
            "day_of_week": parts[4] if parts[4] != "*" else None,
        }

    async def _execute_post(self, post_id: str):
        """Execute a scheduled post"""
        try:
            self.logger.info(f"Executing scheduled post: {post_id}")

            # Load post from database
            post = await self._load_scheduled_post(post_id)
            if not post:
                self.logger.error(f"Post {post_id} not found")
                return

            # Update status
            post.status = PostStatus.PROCESSING
            await self._update_post_status(post)

            # Import and use social distributor
            from social_distributor import SocialMediaDistributor, SocialPost

            distributor = SocialMediaDistributor()

            # Create SocialPost object
            social_post = SocialPost(
                content=post.content,
                media_paths=post.media_files,
                platforms=post.platforms,
                hashtags=post.hashtags,
                mentions=post.mentions,
            )

            # Execute posting
            results = await distributor.post_to_all_platforms(social_post)

            # Check results
            success_count = sum(
                1 for result in results.values() if result.get("success", True)
            )
            total_platforms = len(post.platforms)

            if success_count == total_platforms:
                post.status = PostStatus.POSTED
                post.posted_at = datetime.now(UTC)
                post.error_message = None
            elif success_count > 0:
                post.status = PostStatus.POSTED  # Partial success
                post.posted_at = datetime.now(UTC)
                failed_platforms = [p for p, r in results.items() if r.get("error")]
                post.error_message = f"Failed on platforms: {failed_platforms}"
            else:
                post.status = PostStatus.FAILED
                post.error_message = str(results)

                # Retry if attempts remaining
                if post.retry_count < post.max_retries:
                    await self._schedule_retry(post)
                    return

            # Update post status
            await self._update_post_status(post)

            # Store analytics
            await self._store_posting_analytics(post, results)

            self.logger.info(f"Post {post_id} executed successfully")

        except Exception as e:
            self.logger.error(f"Failed to execute post {post_id}: {e}")

            # Update post as failed and schedule retry if possible
            post = await self._load_scheduled_post(post_id)
            if post:
                post.status = PostStatus.FAILED
                post.error_message = str(e)

                if post.retry_count < post.max_retries:
                    await self._schedule_retry(post)
                else:
                    await self._update_post_status(post)

    async def _schedule_retry(self, post: ScheduledPost):
        """Schedule a retry for failed post"""
        post.retry_count += 1
        # Exponential backoff, max 1 hour
        retry_delay = min(60 * (2**post.retry_count), 3600)

        retry_time = datetime.now(UTC) + timedelta(seconds=retry_delay)
        post.scheduled_time = retry_time

        await self._update_post_status(post)
        await self._schedule_single_post(post)

        self.logger.info(
            f"Scheduled retry {post.retry_count} for post {post.id} at {retry_time}",
        )

    async def _load_scheduled_post(self, post_id: str) -> ScheduledPost | None:
        """Load scheduled post from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM scheduled_posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()

        conn.close()

        if not row:
            return None

        # Convert row to ScheduledPost
        return ScheduledPost(
            id=row[0],
            content=row[1],
            platforms=json.loads(row[2]),
            scheduled_time=datetime.fromisoformat(row[3].replace("Z", "+00:00")),
            status=PostStatus(row[4]),
            media_files=json.loads(row[5]) if row[5] else None,
            hashtags=json.loads(row[6]) if row[6] else None,
            mentions=json.loads(row[7]) if row[7] else None,
            timezone=row[8],
            recurring=bool(row[9]),
            frequency=ScheduleFrequency(row[10]) if row[10] else ScheduleFrequency.ONCE,
            cron_expression=row[11],
            max_retries=row[12],
            retry_count=row[13],
            priority=row[14],
            campaign_id=row[15],
            created_at=(
                datetime.fromisoformat(row[16].replace("Z", "+00:00"))
                if row[16]
                else None
            ),
            updated_at=(
                datetime.fromisoformat(row[17].replace("Z", "+00:00"))
                if row[17]
                else None
            ),
            posted_at=(
                datetime.fromisoformat(row[18].replace("Z", "+00:00"))
                if row[18]
                else None
            ),
            error_message=row[19],
        )

    async def _update_post_status(self, post: ScheduledPost):
        """Update post status in database"""
        post.updated_at = datetime.now(UTC)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE scheduled_posts SET
            status = ?, updated_at = ?, posted_at = ?, error_message = ?, retry_count = ?
            WHERE id = ?
        """,
            (
                post.status.value,
                post.updated_at,
                post.posted_at,
                post.error_message,
                post.retry_count,
                post.id,
            ),
        )

        conn.commit()
        conn.close()

    async def _store_posting_analytics(self, post: ScheduledPost, results: dict):
        """Store posting analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for platform, result in results.items():
            if result.get("success", True):
                cursor.execute(
                    """
                    INSERT INTO posting_analytics
                    (post_id, platform, posted_time)
                    VALUES (?, ?, ?)
                """,
                    (post.id, platform, post.posted_at),
                )

        conn.commit()
        conn.close()

    def start_scheduler(self):
        """Start the scheduler"""
        self.scheduler.start()
        self.logger.info("Social media scheduler started")

    def stop_scheduler(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        self.logger.info("Social media scheduler stopped")

    async def get_scheduled_posts(
        self,
        status: PostStatus = None,
        platform: str = None,
        limit: int = 100,
    ) -> list[ScheduledPost]:
        """Get scheduled posts with optional filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM scheduled_posts WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if platform:
            query += " AND platforms LIKE ?"
            params.append(f"%{platform}%")

        query += " ORDER BY scheduled_time ASC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        posts = []
        for row in rows:
            post = await self._row_to_scheduled_post(row)
            if post:
                posts.append(post)

        return posts

    async def _row_to_scheduled_post(self, row) -> ScheduledPost | None:
        """Convert database row to ScheduledPost"""
        try:
            return ScheduledPost(
                id=row[0],
                content=row[1],
                platforms=json.loads(row[2]),
                scheduled_time=datetime.fromisoformat(row[3].replace("Z", "+00:00")),
                status=PostStatus(row[4]),
                media_files=json.loads(row[5]) if row[5] else None,
                hashtags=json.loads(row[6]) if row[6] else None,
                mentions=json.loads(row[7]) if row[7] else None,
                timezone=row[8] or "UTC",
                recurring=bool(row[9]),
                frequency=(
                    ScheduleFrequency(row[10]) if row[10] else ScheduleFrequency.ONCE
                ),
                cron_expression=row[11],
                max_retries=row[12] or 3,
                retry_count=row[13] or 0,
                priority=row[14] or 1,
                campaign_id=row[15],
                created_at=(
                    datetime.fromisoformat(row[16].replace("Z", "+00:00"))
                    if row[16]
                    else None
                ),
                updated_at=(
                    datetime.fromisoformat(row[17].replace("Z", "+00:00"))
                    if row[17]
                    else None
                ),
                posted_at=(
                    datetime.fromisoformat(row[18].replace("Z", "+00:00"))
                    if row[18]
                    else None
                ),
                error_message=row[19],
                engagement_tracking=bool(row[20]) if row[20] is not None else True,
            )
        except Exception as e:
            self.logger.error(f"Error converting row to ScheduledPost: {e}")
            return None

    async def cancel_post(self, post_id: str) -> bool:
        """Cancel a scheduled post"""
        try:
            # Remove from scheduler
            try:
                self.scheduler.remove_job(post_id)
            except BaseException:
                pass  # Job might not exist in scheduler

            # Update status in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE scheduled_posts
                SET status = ?, updated_at = ?
                WHERE id = ? AND status IN ('draft', 'scheduled')
            """,
                (PostStatus.CANCELLED.value, datetime.now(UTC), post_id),
            )

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            if success:
                self.logger.info(f"Post {post_id} cancelled")

            return success

        except Exception as e:
            self.logger.error(f"Failed to cancel post {post_id}: {e}")
            return False

    async def get_posting_analytics(self, days: int = 30) -> dict:
        """Get posting analytics summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        # Get posting stats
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_posts,
                COUNT(CASE WHEN status = 'posted' THEN 1 END) as successful_posts,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_posts,
                COUNT(CASE WHEN status = 'scheduled' THEN 1 END) as pending_posts
            FROM scheduled_posts
            WHERE created_at >= ?
        """,
            (start_date,),
        )

        stats = cursor.fetchone()

        # Get platform breakdown
        cursor.execute(
            """
            SELECT platforms, COUNT(*)
            FROM scheduled_posts
            WHERE created_at >= ? AND status = 'posted'
            GROUP BY platforms
        """,
            (start_date,),
        )

        platform_stats = cursor.fetchall()

        conn.close()

        return {
            "total_posts": stats[0],
            "successful_posts": stats[1],
            "failed_posts": stats[2],
            "pending_posts": stats[3],
            "success_rate": (stats[1] / stats[0] * 100) if stats[0] > 0 else 0,
            "platform_breakdown": dict(platform_stats) if platform_stats else {},
            "period_days": days,
        }


# Usage example


async def demo_scheduler():
    """Demonstrate scheduler functionality"""

    # Initialize scheduler
    scheduler = SocialSchedulerSystem()
    scheduler.start_scheduler()

    # Create a scheduled post
    post = ScheduledPost(
        content="🚀 Exciting news! Our new automation feature is now live! It's already helping teams save hours of manual work. What's your biggest time-waster that you'd love to automate? #automation #productivity #innovation",
        platforms=["twitter", "linkedin"],
        scheduled_time=datetime.now(UTC) + timedelta(minutes=5),
        status=PostStatus.SCHEDULED,
        hashtags=["#automation", "#productivity", "#innovation"],
        priority=1,
        campaign_id="product_launch_2024",
    )

    # Schedule the post
    post_id = await scheduler.schedule_post(post)
    print(f"Scheduled post: {post_id}")

    # Get scheduled posts
    scheduled = await scheduler.get_scheduled_posts(status=PostStatus.SCHEDULED)
    print(f"Found {len(scheduled)} scheduled posts")

    # Get analytics
    analytics = await scheduler.get_posting_analytics(days=30)
    print(f"Analytics: {json.dumps(analytics, indent=2)}")

    # Wait a bit, then stop
    await asyncio.sleep(10)
    scheduler.stop_scheduler()


if __name__ == "__main__":
    asyncio.run(demo_scheduler())
