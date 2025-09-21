#!/usr/bin/env python3
"""
Social Media Listening System
Advanced social listening, sentiment analysis, and trend detection
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

# NLP and sentiment analysis
try:
    import matplotlib.pyplot as plt
    import nltk
    import praw
    import requests
    import seaborn as sns
    import tweepy
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from textblob import TextBlob
    from wordcloud import WordCloud
except ImportError:
    print(
        "Social listening dependencies not installed. Run: pip install tweepy praw textblob nltk wordcloud matplotlib seaborn scikit-learn",
    )


@dataclass
class SocialMention:
    """Social media mention data structure"""

    id: str
    platform: str
    author: str
    content: str
    timestamp: datetime
    url: str
    engagement_metrics: dict  # likes, shares, comments, etc.
    sentiment_score: float
    sentiment_label: str  # positive, negative, neutral
    keywords: list[str]
    hashtags: list[str]
    mentions: list[str]
    language: str
    location: str = None
    influence_score: float = 0.0  # author's influence score
    reach: int = 0
    verified_author: bool = False


@dataclass
class TrendingTopic:
    """Trending topic data structure"""

    topic: str
    platform: str
    mention_count: int
    growth_rate: float
    sentiment_distribution: dict[str, int]
    avg_engagement: float
    top_keywords: list[str]
    sample_posts: list[str]
    trend_score: float
    category: str = None


@dataclass
class InfluencerProfile:
    """Influencer profile data structure"""

    username: str
    platform: str
    follower_count: int
    engagement_rate: float
    avg_likes: float
    avg_comments: float
    content_categories: list[str]
    posting_frequency: float
    verified: bool
    influence_score: float
    recent_topics: list[str]


class SocialListeningSystem:
    """Advanced social media listening and monitoring system"""

    def __init__(self, db_path: str = "social_listening.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

        # Initialize database
        self._init_database()

        # Platform clients
        self.clients = {}
        self._initialize_clients()

        # Monitoring keywords and phrases
        self.monitoring_keywords = set()
        self.competing_brands = set()
        self.brand_mentions = set()

        # Sentiment thresholds
        self.sentiment_thresholds = {
            "very_positive": 0.5,
            "positive": 0.1,
            "neutral": (-0.1, 0.1),
            "negative": -0.1,
            "very_negative": -0.5,
        }

        # Load NLTK data
        try:
            nltk.download("vader_lexicon", quiet=True)
            nltk.download("punkt", quiet=True)
            nltk.download("stopwords", quiet=True)
            from nltk.sentiment import SentimentIntensityAnalyzer

            self.sentiment_analyzer = SentimentIntensityAnalyzer()
        except BaseException:
            self.sentiment_analyzer = None

    def _init_database(self):
        """Initialize SQLite database for social listening"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Mentions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS social_mentions (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                url TEXT,
                engagement_metrics TEXT,
                sentiment_score REAL,
                sentiment_label TEXT,
                keywords TEXT,
                hashtags TEXT,
                mentions TEXT,
                language TEXT,
                location TEXT,
                influence_score REAL DEFAULT 0.0,
                reach INTEGER DEFAULT 0,
                verified_author BOOLEAN DEFAULT FALSE,
                raw_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_platform_timestamp (platform, timestamp),
                INDEX idx_sentiment (sentiment_label),
                INDEX idx_keywords (keywords)
            )
        """,
        )

        # Trending topics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trending_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                platform TEXT NOT NULL,
                mention_count INTEGER,
                growth_rate REAL,
                sentiment_distribution TEXT,
                avg_engagement REAL,
                top_keywords TEXT,
                sample_posts TEXT,
                trend_score REAL,
                category TEXT,
                date DATE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_platform_date (platform, date),
                INDEX idx_trend_score (trend_score)
            )
        """,
        )

        # Influencers table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS influencers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                platform TEXT NOT NULL,
                follower_count INTEGER,
                engagement_rate REAL,
                avg_likes REAL,
                avg_comments REAL,
                content_categories TEXT,
                posting_frequency REAL,
                verified BOOLEAN DEFAULT FALSE,
                influence_score REAL,
                recent_topics TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, platform),
                INDEX idx_influence_score (influence_score),
                INDEX idx_platform (platform)
            )
        """,
        )

        # Keywords monitoring table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monitoring_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                category TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(keyword)
            )
        """,
        )

        # Alerts table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS social_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                platform TEXT,
                trigger_keyword TEXT,
                content TEXT,
                severity TEXT DEFAULT 'medium',
                acknowledged BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_alert_type (alert_type),
                INDEX idx_acknowledged (acknowledged)
            )
        """,
        )

        conn.commit()
        conn.close()

    def _initialize_clients(self):
        """Initialize social media API clients"""
        # Twitter client
        twitter_config = {
            "bearer_token": os.getenv("TWITTER_BEARER_TOKEN"),
            "consumer_key": os.getenv("TWITTER_API_KEY"),
            "consumer_secret": os.getenv("TWITTER_API_SECRET"),
            "access_token": os.getenv("TWITTER_ACCESS_TOKEN"),
            "access_token_secret": os.getenv("TWITTER_ACCESS_SECRET"),
        }

        if twitter_config["bearer_token"]:
            try:
                self.clients["twitter"] = tweepy.Client(
                    bearer_token=twitter_config["bearer_token"],
                    consumer_key=twitter_config["consumer_key"],
                    consumer_secret=twitter_config["consumer_secret"],
                    access_token=twitter_config["access_token"],
                    access_token_secret=twitter_config["access_token_secret"],
                    wait_on_rate_limit=True,
                )
                self.logger.info("Twitter listening client initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Twitter client: {e}")

        # Reddit client
        reddit_config = {
            "client_id": os.getenv("REDDIT_CLIENT_ID"),
            "client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
            "user_agent": os.getenv("REDDIT_USER_AGENT", "SocialListening/1.0"),
        }

        if reddit_config["client_id"]:
            try:
                self.clients["reddit"] = praw.Reddit(
                    client_id=reddit_config["client_id"],
                    client_secret=reddit_config["client_secret"],
                    user_agent=reddit_config["user_agent"],
                )
                self.logger.info("Reddit listening client initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Reddit client: {e}")

    async def add_monitoring_keywords(self, keywords: list[str], category: str = None):
        """Add keywords to monitoring list"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for keyword in keywords:
            cursor.execute(
                """
                INSERT OR IGNORE INTO monitoring_keywords (keyword, category)
                VALUES (?, ?)
            """,
                (keyword, category),
            )
            self.monitoring_keywords.add(keyword.lower())

        conn.commit()
        conn.close()

        self.logger.info(f"Added {len(keywords)} keywords to monitoring")

    async def start_listening(self, duration_hours: int = 24):
        """Start social media listening for specified duration"""
        self.logger.info(f"Starting social listening for {duration_hours} hours")

        end_time = datetime.now() + timedelta(hours=duration_hours)

        while datetime.now() < end_time:
            try:
                # Listen on all platforms
                await asyncio.gather(
                    self._listen_twitter(),
                    self._listen_reddit(),
                    self._detect_trending_topics(),
                    self._monitor_influencers(),
                )

                # Wait before next cycle
                await asyncio.sleep(300)  # 5 minutes between cycles

            except Exception as e:
                self.logger.error(f"Error in listening cycle: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

        self.logger.info("Social listening session completed")

    async def _listen_twitter(self):
        """Listen for mentions and keywords on Twitter"""
        if "twitter" not in self.clients:
            return

        client = self.clients["twitter"]

        try:
            # Search for monitoring keywords
            for keyword in list(self.monitoring_keywords)[
                :10
            ]:  # Limit to avoid rate limits
                tweets = client.search_recent_tweets(
                    query=f'"{keyword}" -is:retweet lang:en',
                    tweet_fields=["created_at", "public_metrics", "author_id", "geo"],
                    user_fields=["verified", "public_metrics"],
                    max_results=10,
                )

                if tweets.data:
                    for tweet in tweets.data:
                        mention = await self._process_twitter_mention(
                            tweet,
                            tweets.includes,
                        )
                        if mention:
                            await self._store_mention(mention)
                            await self._check_alert_conditions(mention)

                # Rate limiting
                await asyncio.sleep(2)

        except Exception as e:
            self.logger.error(f"Twitter listening error: {e}")

    async def _process_twitter_mention(
        self,
        tweet,
        includes,
    ) -> SocialMention | None:
        """Process a Twitter mention into structured data"""
        try:
            # Get author info
            author_info = None
            if includes and "users" in includes:
                author_info = next(
                    (u for u in includes["users"] if u.id == tweet.author_id),
                    None,
                )

            # Extract text content
            content = tweet.text

            # Sentiment analysis
            sentiment_score, sentiment_label = self._analyze_sentiment(content)

            # Extract keywords, hashtags, mentions
            keywords = self._extract_keywords(content)
            hashtags = re.findall(r"#\w+", content)
            mentions = re.findall(r"@\w+", content)

            # Calculate influence score
            influence_score = 0.0
            if author_info:
                followers = author_info.public_metrics.get("followers_count", 0)
                influence_score = min(100, followers / 1000)  # Simple influence scoring

            return SocialMention(
                id=f"twitter_{tweet.id}",
                platform="twitter",
                author=author_info.username if author_info else str(tweet.author_id),
                content=content,
                timestamp=tweet.created_at,
                url=f"https://twitter.com/user/status/{tweet.id}",
                engagement_metrics=tweet.public_metrics,
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                keywords=keywords,
                hashtags=hashtags,
                mentions=mentions,
                language="en",
                influence_score=influence_score,
                verified_author=author_info.verified if author_info else False,
                reach=tweet.public_metrics.get("impression_count", 0),
            )

        except Exception as e:
            self.logger.error(f"Error processing Twitter mention: {e}")
            return None

    async def _listen_reddit(self):
        """Listen for mentions and keywords on Reddit"""
        if "reddit" not in self.clients:
            return

        reddit = self.clients["reddit"]

        try:
            # Search across popular subreddits
            subreddits = ["all", "popular", "technology", "business", "automation"]

            for keyword in list(self.monitoring_keywords)[:5]:  # Limit keywords
                for subreddit_name in subreddits[:2]:  # Limit subreddits
                    try:
                        subreddit = reddit.subreddit(subreddit_name)

                        # Search recent posts
                        for submission in subreddit.search(
                            keyword,
                            time_filter="day",
                            limit=5,
                        ):
                            mention = await self._process_reddit_mention(
                                submission,
                                "post",
                            )
                            if mention:
                                await self._store_mention(mention)
                                await self._check_alert_conditions(mention)

                        await asyncio.sleep(1)  # Rate limiting

                    except Exception as e:
                        self.logger.warning(
                            f"Error searching subreddit {subreddit_name}: {e}",
                        )
                        continue

        except Exception as e:
            self.logger.error(f"Reddit listening error: {e}")

    async def _process_reddit_mention(
        self,
        submission,
        content_type: str,
    ) -> SocialMention | None:
        """Process a Reddit mention into structured data"""
        try:
            content = submission.title
            if hasattr(submission, "selftext") and submission.selftext:
                content += " " + submission.selftext

            # Sentiment analysis
            sentiment_score, sentiment_label = self._analyze_sentiment(content)

            # Extract keywords
            keywords = self._extract_keywords(content)

            return SocialMention(
                id=f"reddit_{submission.id}",
                platform="reddit",
                author=str(submission.author) if submission.author else "deleted",
                content=content,
                timestamp=datetime.fromtimestamp(submission.created_utc),
                url=submission.url,
                engagement_metrics={
                    "score": submission.score,
                    "upvote_ratio": submission.upvote_ratio,
                    "num_comments": submission.num_comments,
                },
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                keywords=keywords,
                hashtags=[],  # Reddit doesn't use hashtags
                mentions=[],
                language="en",
                influence_score=min(100, submission.score / 10),  # Simple scoring
                reach=submission.view_count or 0,
            )

        except Exception as e:
            self.logger.error(f"Error processing Reddit mention: {e}")
            return None

    def _analyze_sentiment(self, text: str) -> tuple[float, str]:
        """Analyze sentiment of text"""
        try:
            if self.sentiment_analyzer:
                # Use NLTK VADER
                scores = self.sentiment_analyzer.polarity_scores(text)
                compound_score = scores["compound"]
            else:
                # Fallback to TextBlob
                blob = TextBlob(text)
                compound_score = blob.sentiment.polarity

            # Classify sentiment
            if compound_score >= self.sentiment_thresholds["very_positive"]:
                label = "very_positive"
            elif compound_score >= self.sentiment_thresholds["positive"]:
                label = "positive"
            elif compound_score <= self.sentiment_thresholds["very_negative"]:
                label = "very_negative"
            elif compound_score <= self.sentiment_thresholds["negative"]:
                label = "negative"
            else:
                label = "neutral"

            return compound_score, label

        except Exception as e:
            self.logger.warning(f"Sentiment analysis failed: {e}")
            return 0.0, "neutral"

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract relevant keywords from text"""
        try:
            # Simple keyword extraction
            words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

            # Filter out common stop words
            stop_words = {
                "the",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
                "from",
                "this",
                "that",
                "these",
                "those",
                "is",
                "are",
                "was",
                "were",
                "been",
                "being",
                "have",
                "has",
                "had",
            }

            keywords = [word for word in words if word not in stop_words]

            # Return most frequent keywords
            word_freq = Counter(keywords)
            return [word for word, count in word_freq.most_common(10)]

        except Exception as e:
            self.logger.warning(f"Keyword extraction failed: {e}")
            return []

    async def _store_mention(self, mention: SocialMention):
        """Store mention in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO social_mentions (
                id, platform, author, content, timestamp, url, engagement_metrics,
                sentiment_score, sentiment_label, keywords, hashtags, mentions,
                language, location, influence_score, reach, verified_author, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                mention.id,
                mention.platform,
                mention.author,
                mention.content,
                mention.timestamp,
                mention.url,
                json.dumps(mention.engagement_metrics),
                mention.sentiment_score,
                mention.sentiment_label,
                json.dumps(mention.keywords),
                json.dumps(mention.hashtags),
                json.dumps(mention.mentions),
                mention.language,
                mention.location,
                mention.influence_score,
                mention.reach,
                mention.verified_author,
                json.dumps(asdict(mention)),
            ),
        )

        conn.commit()
        conn.close()

    async def _check_alert_conditions(self, mention: SocialMention):
        """Check if mention triggers any alerts"""
        alerts = []

        # Negative sentiment alert
        if (
            mention.sentiment_label in ["negative", "very_negative"]
            and mention.influence_score > 10
        ):
            alerts.append(
                {
                    "type": "negative_sentiment",
                    "severity": (
                        "high"
                        if mention.sentiment_label == "very_negative"
                        else "medium"
                    ),
                    "content": f"Negative mention by {mention.author}: {mention.content[:100]}...",
                },
            )

        # High influence mention
        if mention.influence_score > 50:
            alerts.append(
                {
                    "type": "high_influence_mention",
                    "severity": "high",
                    "content": f"High-influence mention by {mention.author} (score: {mention.influence_score})",
                },
            )

        # Viral content alert
        engagement_total = (
            sum(mention.engagement_metrics.values())
            if mention.engagement_metrics
            else 0
        )
        if engagement_total > 1000:
            alerts.append(
                {
                    "type": "viral_content",
                    "severity": "medium",
                    "content": f"Viral mention with {engagement_total} total engagement",
                },
            )

        # Store alerts
        for alert in alerts:
            await self._store_alert(alert, mention)

    async def _store_alert(self, alert: dict, mention: SocialMention):
        """Store alert in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO social_alerts (alert_type, platform, trigger_keyword, content, severity)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                alert["type"],
                mention.platform,
                mention.keywords[0] if mention.keywords else None,
                alert["content"],
                alert["severity"],
            ),
        )

        conn.commit()
        conn.close()

        self.logger.warning(f"ALERT [{alert['severity'].upper()}]: {alert['content']}")

    async def _detect_trending_topics(self):
        """Detect trending topics across platforms"""
        try:
            # Get recent mentions (last 24 hours)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            yesterday = datetime.now() - timedelta(days=1)
            cursor.execute(
                """
                SELECT keywords, platform, sentiment_label, engagement_metrics
                FROM social_mentions
                WHERE timestamp >= ?
            """,
                (yesterday,),
            )

            rows = cursor.fetchall()
            conn.close()

            # Analyze trending keywords by platform
            platform_keywords = defaultdict(lambda: defaultdict(list))

            for row in rows:
                keywords = json.loads(row[0]) if row[0] else []
                platform = row[1]
                sentiment = row[2]
                engagement = json.loads(row[3]) if row[3] else {}

                for keyword in keywords:
                    platform_keywords[platform][keyword].append(
                        {
                            "sentiment": sentiment,
                            "engagement": sum(engagement.values()) if engagement else 0,
                        },
                    )

            # Calculate trend scores and store trending topics
            for platform, keywords_data in platform_keywords.items():
                trending = []

                for keyword, mentions in keywords_data.items():
                    if len(mentions) >= 3:  # Minimum mentions to be considered trending
                        mention_count = len(mentions)
                        avg_engagement = (
                            sum(m["engagement"] for m in mentions) / mention_count
                        )
                        sentiment_dist = Counter(m["sentiment"] for m in mentions)

                        # Calculate trend score
                        trend_score = mention_count * 0.7 + (avg_engagement / 100) * 0.3

                        trending.append(
                            TrendingTopic(
                                topic=keyword,
                                platform=platform,
                                mention_count=mention_count,
                                growth_rate=0.0,  # Would need historical data
                                sentiment_distribution=dict(sentiment_dist),
                                avg_engagement=avg_engagement,
                                top_keywords=[keyword],
                                sample_posts=[],
                                trend_score=trend_score,
                            ),
                        )

                # Store top trending topics
                trending.sort(key=lambda x: x.trend_score, reverse=True)
                for topic in trending[:10]:  # Top 10 per platform
                    await self._store_trending_topic(topic)

        except Exception as e:
            self.logger.error(f"Trend detection error: {e}")

    async def _store_trending_topic(self, topic: TrendingTopic):
        """Store trending topic in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO trending_topics (
                topic, platform, mention_count, growth_rate, sentiment_distribution,
                avg_engagement, top_keywords, sample_posts, trend_score, category, date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                topic.topic,
                topic.platform,
                topic.mention_count,
                topic.growth_rate,
                json.dumps(topic.sentiment_distribution),
                topic.avg_engagement,
                json.dumps(topic.top_keywords),
                json.dumps(topic.sample_posts),
                topic.trend_score,
                topic.category,
                datetime.now().date(),
            ),
        )

        conn.commit()
        conn.close()

    async def _monitor_influencers(self):
        """Monitor key influencers and their content"""
        # This would involve tracking specific accounts
        # Implementation would depend on having a list of influencers to monitor

    async def get_sentiment_analysis(self, days: int = 7, platform: str = None) -> dict:
        """Get sentiment analysis summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        start_date = datetime.now() - timedelta(days=days)

        query = """
            SELECT sentiment_label, COUNT(*), AVG(sentiment_score), platform
            FROM social_mentions
            WHERE timestamp >= ?
        """
        params = [start_date]

        if platform:
            query += " AND platform = ?"
            params.append(platform)

        query += (
            " GROUP BY sentiment_label, platform ORDER BY platform, sentiment_label"
        )

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        # Process results
        sentiment_data = defaultdict(lambda: defaultdict(dict))

        for row in results:
            sentiment_label, count, avg_score, plat = row
            sentiment_data[plat][sentiment_label] = {
                "count": count,
                "avg_score": avg_score,
            }

        return dict(sentiment_data)

    async def get_trending_topics(
        self,
        platform: str = None,
        days: int = 1,
    ) -> list[TrendingTopic]:
        """Get trending topics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        start_date = datetime.now().date() - timedelta(days=days)

        query = """
            SELECT * FROM trending_topics
            WHERE date >= ?
        """
        params = [start_date]

        if platform:
            query += " AND platform = ?"
            params.append(platform)

        query += " ORDER BY trend_score DESC LIMIT 50"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        trending_topics = []
        for row in rows:
            topic = TrendingTopic(
                topic=row[1],
                platform=row[2],
                mention_count=row[3],
                growth_rate=row[4],
                sentiment_distribution=json.loads(row[5]) if row[5] else {},
                avg_engagement=row[6],
                top_keywords=json.loads(row[7]) if row[7] else [],
                sample_posts=json.loads(row[8]) if row[8] else [],
                trend_score=row[9],
                category=row[10],
            )
            trending_topics.append(topic)

        return trending_topics

    async def get_alerts(
        self,
        acknowledged: bool = False,
        severity: str = None,
    ) -> list[dict]:
        """Get social media alerts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM social_alerts WHERE acknowledged = ?"
        params = [acknowledged]

        if severity:
            query += " AND severity = ?"
            params.append(severity)

        query += " ORDER BY created_at DESC LIMIT 100"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        alerts = []
        for row in rows:
            alerts.append(
                {
                    "id": row[0],
                    "type": row[1],
                    "platform": row[2],
                    "trigger_keyword": row[3],
                    "content": row[4],
                    "severity": row[5],
                    "acknowledged": bool(row[6]),
                    "created_at": row[7],
                },
            )

        return alerts

    async def acknowledge_alert(self, alert_id: int) -> bool:
        """Acknowledge an alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE social_alerts
            SET acknowledged = TRUE
            WHERE id = ?
        """,
            (alert_id,),
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    async def generate_listening_report(self, days: int = 7) -> dict:
        """Generate comprehensive listening report"""
        return {
            "sentiment_analysis": await self.get_sentiment_analysis(days),
            "trending_topics": await self.get_trending_topics(days=days),
            "alerts": await self.get_alerts(),
            "summary": await self._get_listening_summary(days),
        }

    async def _get_listening_summary(self, days: int) -> dict:
        """Get listening summary statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        start_date = datetime.now() - timedelta(days=days)

        # Total mentions
        cursor.execute(
            """
            SELECT COUNT(*), platform
            FROM social_mentions
            WHERE timestamp >= ?
            GROUP BY platform
        """,
            (start_date,),
        )
        platform_counts = dict(cursor.fetchall())

        # Sentiment distribution
        cursor.execute(
            """
            SELECT sentiment_label, COUNT(*)
            FROM social_mentions
            WHERE timestamp >= ?
            GROUP BY sentiment_label
        """,
            (start_date,),
        )
        sentiment_counts = dict(cursor.fetchall())

        # Top keywords
        cursor.execute(
            """
            SELECT keywords
            FROM social_mentions
            WHERE timestamp >= ?
        """,
            (start_date,),
        )
        all_keywords = []
        for row in cursor.fetchall():
            if row[0]:
                keywords = json.loads(row[0])
                all_keywords.extend(keywords)

        top_keywords = [word for word, count in Counter(all_keywords).most_common(10)]

        conn.close()

        return {
            "total_mentions": sum(platform_counts.values()),
            "platform_breakdown": platform_counts,
            "sentiment_distribution": sentiment_counts,
            "top_keywords": top_keywords,
            "monitoring_period_days": days,
        }


# Usage example


async def demo_social_listening():
    """Demonstrate social listening functionality"""

    # Initialize listening system
    listener = SocialListeningSystem()

    # Add monitoring keywords
    await listener.add_monitoring_keywords(
        ["automation", "AI", "productivity", "efficiency", "workflow"],
        "tech",
    )

    # Start listening for a short period (demo)
    print("Starting social listening demo...")

    # Simulate listening (in real use, this would run continuously)
    await listener._listen_twitter()
    await listener._listen_reddit()
    await listener._detect_trending_topics()

    # Generate report
    report = await listener.generate_listening_report(days=1)

    print("=== Social Listening Report ===")
    print(f"Summary: {json.dumps(report['summary'], indent=2)}")
    print(f"Sentiment Analysis: {json.dumps(report['sentiment_analysis'], indent=2)}")
    print(f"Trending Topics: {len(report['trending_topics'])} topics found")
    print(f"Alerts: {len(report['alerts'])} alerts generated")


if __name__ == "__main__":
    asyncio.run(demo_social_listening())
