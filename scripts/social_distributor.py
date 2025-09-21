#!/usr/bin/env python3
"""
Social Media Distribution Network
Automated multi-platform posting system with content optimization
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime

# Platform-specific imports (install with pip install -r requirements_social.txt)
try:
    from urllib.parse import urlparse

    import praw
    import requests
    import schedule
    import tweepy
    from PIL import Image
except ImportError as e:
    logging.warning(f"Some dependencies not installed: {e}")
    logging.info("Run: pip install -r requirements_social.txt")


@dataclass
class SocialPost:
    """Data class for social media posts"""

    content: str
    media_paths: list[str] = None
    platforms: list[str] = None
    scheduled_time: datetime = None
    hashtags: list[str] = None
    mentions: list[str] = None
    metadata: dict = None


class SocialMediaDistributor:
    """Main class for multi-platform social media distribution"""

    def __init__(self, config_path: str = None):
        """Initialize with configuration"""
        self.config = self._load_config(config_path)
        self.platforms = {}
        self.posting_schedule = self._generate_optimal_schedule()
        self.rate_limits = self._setup_rate_limits()
        self.analytics = {}

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("../logs/social_distributor.log"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

        # Initialize platforms
        self._initialize_platforms()

    def _load_config(self, config_path: str = None) -> dict:
        """Load configuration from file or environment"""
        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                return json.load(f)

        # Default configuration with environment variables
        return {
            "twitter": {
                "api_key": os.getenv("TWITTER_API_KEY"),
                "api_secret": os.getenv("TWITTER_API_SECRET"),
                "access_token": os.getenv("TWITTER_ACCESS_TOKEN"),
                "access_secret": os.getenv("TWITTER_ACCESS_SECRET"),
                "bearer_token": os.getenv("TWITTER_BEARER_TOKEN"),
            },
            "reddit": {
                "client_id": os.getenv("REDDIT_CLIENT_ID"),
                "client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
                "user_agent": os.getenv("REDDIT_USER_AGENT", "VibeBot/1.0"),
                "username": os.getenv("REDDIT_USERNAME"),
                "REDACTED_SECRET": os.getenv("REDDIT_PASSWORD"),
            },
            "instagram": {
                "access_token": os.getenv("INSTAGRAM_ACCESS_TOKEN"),
                "business_account_id": os.getenv("INSTAGRAM_BUSINESS_ID"),
            },
            "tiktok": {
                "access_token": os.getenv("TIKTOK_ACCESS_TOKEN"),
                "client_key": os.getenv("TIKTOK_CLIENT_KEY"),
            },
            "linkedin": {
                "access_token": os.getenv("LINKEDIN_ACCESS_TOKEN"),
                "organization_id": os.getenv("LINKEDIN_ORG_ID"),
            },
        }

    def _initialize_platforms(self):
        """Initialize all configured social media platform clients"""

        # Twitter/X initialization
        if all(self.config.get("twitter", {}).values()):
            try:
                # Twitter API v2 client
                self.platforms["twitter"] = tweepy.Client(
                    bearer_token=self.config["twitter"]["bearer_token"],
                    consumer_key=self.config["twitter"]["api_key"],
                    consumer_secret=self.config["twitter"]["api_secret"],
                    access_token=self.config["twitter"]["access_token"],
                    access_token_secret=self.config["twitter"]["access_secret"],
                    wait_on_rate_limit=True,
                )
                self.logger.info("Twitter/X client initialized")
            except Exception as e:
                self.logger.error(f"Twitter initialization failed: {e}")

        # Reddit initialization
        if all(self.config.get("reddit", {}).values()):
            try:
                self.platforms["reddit"] = praw.Reddit(
                    client_id=self.config["reddit"]["client_id"],
                    client_secret=self.config["reddit"]["client_secret"],
                    user_agent=self.config["reddit"]["user_agent"],
                    username=self.config["reddit"]["username"],
                    REDACTED_SECRET=self.config["reddit"]["REDACTED_SECRET"],
                )
                self.logger.info("Reddit client initialized")
            except Exception as e:
                self.logger.error(f"Reddit initialization failed: {e}")

        # Instagram Graph API initialization
        if self.config.get("instagram", {}).get("access_token"):
            self.platforms["instagram"] = {
                "access_token": self.config["instagram"]["access_token"],
                "business_account_id": self.config["instagram"]["business_account_id"],
            }
            self.logger.info("Instagram client initialized")

        # LinkedIn initialization
        if self.config.get("linkedin", {}).get("access_token"):
            self.platforms["linkedin"] = {
                "access_token": self.config["linkedin"]["access_token"],
                "organization_id": self.config["linkedin"]["organization_id"],
            }
            self.logger.info("LinkedIn client initialized")

    def _generate_optimal_schedule(self) -> dict[str, list[str]]:
        """Generate optimal posting times based on platform best practices"""
        return {
            "twitter": ["09:00", "12:00", "15:00", "17:00", "20:00"],
            "instagram": ["11:00", "14:00", "17:00", "19:00"],
            "reddit": ["08:00", "12:00", "17:00", "21:00"],
            "linkedin": ["08:00", "10:00", "12:00", "17:00"],
            "tiktok": ["06:00", "10:00", "16:00", "19:00", "22:00"],
        }

    def _setup_rate_limits(self) -> dict:
        """Setup rate limiting configurations for each platform"""
        return {
            "twitter": {"requests_per_hour": 300, "requests_per_day": 2400},
            "reddit": {"requests_per_minute": 60},
            "instagram": {"requests_per_hour": 200},
            "linkedin": {"requests_per_day": 500},
            "tiktok": {"requests_per_hour": 100},
        }

    async def post_to_all_platforms(self, post: SocialPost) -> dict[str, dict]:
        """Post content to all configured platforms asynchronously"""
        results = {}
        platforms_to_post = post.platforms or list(self.platforms.keys())

        tasks = []
        for platform_name in platforms_to_post:
            if platform_name in self.platforms:
                task = asyncio.create_task(self._post_to_platform(platform_name, post))
                tasks.append((platform_name, task))

        # Execute all posts concurrently
        for platform_name, task in tasks:
            try:
                result = await task
                results[platform_name] = result
                self.logger.info(f"Successfully posted to {platform_name}")
            except Exception as e:
                results[platform_name] = {"error": str(e)}
                self.logger.error(f"Failed to post to {platform_name}: {e}")

            # Rate limiting delay
            await asyncio.sleep(2)

        return results

    async def _post_to_platform(self, platform: str, post: SocialPost) -> dict:
        """Post to a specific platform"""
        if platform == "twitter":
            return await self._post_to_twitter(post)
        if platform == "reddit":
            return await self._post_to_reddit(post)
        if platform == "instagram":
            return await self._post_to_instagram(post)
        if platform == "linkedin":
            return await self._post_to_linkedin(post)
        raise ValueError(f"Unsupported platform: {platform}")

    async def _post_to_twitter(self, post: SocialPost) -> dict:
        """Post to Twitter with thread support"""
        client = self.platforms["twitter"]
        content = self._format_content_for_platform(post.content, "twitter")

        try:
            # Handle media attachments
            media_ids = []
            if post.media_paths:
                for media_path in post.media_paths[:4]:  # Twitter allows max 4 images
                    if os.path.exists(media_path):
                        # Use API v1.1 for media upload
                        auth = tweepy.OAuthHandler(
                            self.config["twitter"]["api_key"],
                            self.config["twitter"]["api_secret"],
                        )
                        auth.set_access_token(
                            self.config["twitter"]["access_token"],
                            self.config["twitter"]["access_secret"],
                        )
                        api_v1 = tweepy.API(auth)
                        media = api_v1.media_upload(media_path)
                        media_ids.append(media.media_id)

            # Handle long content with threads
            if len(content) > 280:
                tweets = self._split_into_tweets(content)
                thread_results = []

                for i, tweet_text in enumerate(tweets):
                    if i == 0:
                        # First tweet with media
                        tweet = client.create_tweet(
                            text=tweet_text,
                            media_ids=media_ids if media_ids else None,
                        )
                    else:
                        # Reply to previous tweet
                        tweet = client.create_tweet(
                            text=tweet_text,
                            in_reply_to_tweet_id=thread_results[-1]["id"],
                        )
                    thread_results.append({"id": tweet.data["id"], "text": tweet_text})

                return {
                    "success": True,
                    "thread_id": thread_results[0]["id"],
                    "tweets": len(thread_results),
                    "url": f"https://twitter.com/user/status/{thread_results[0]['id']}",
                }
            # Single tweet
            tweet = client.create_tweet(
                text=content,
                media_ids=media_ids if media_ids else None,
            )
            return {
                "success": True,
                "tweet_id": tweet.data["id"],
                "url": f"https://twitter.com/user/status/{tweet.data['id']}",
            }

        except Exception as e:
            raise Exception(f"Twitter posting failed: {e}")

    async def _post_to_reddit(self, post: SocialPost) -> dict:
        """Post to relevant subreddits"""
        reddit = self.platforms["reddit"]

        try:
            # Default to test subreddit if none specified
            subreddits = post.metadata.get("subreddits", ["test"])
            results = []

            for subreddit_name in subreddits:
                subreddit = reddit.subreddit(subreddit_name)

                if post.media_paths and len(post.media_paths) > 0:
                    # Image post
                    submission = subreddit.submit_image(
                        title=post.metadata.get("title", post.content[:100]),
                        image_path=post.media_paths[0],
                    )
                else:
                    # Text post
                    submission = subreddit.submit(
                        title=post.metadata.get("title", post.content[:100]),
                        selftext=post.content,
                    )

                results.append(
                    {
                        "subreddit": subreddit_name,
                        "submission_id": submission.id,
                        "url": submission.url,
                        "permalink": f"https://reddit.com{submission.permalink}",
                    },
                )

            return {"success": True, "submissions": results}

        except Exception as e:
            raise Exception(f"Reddit posting failed: {e}")

    async def _post_to_instagram(self, post: SocialPost) -> dict:
        """Post to Instagram using Graph API"""
        config = self.platforms["instagram"]

        try:
            if not post.media_paths:
                raise ValueError("Instagram requires at least one image or video")

            media_path = post.media_paths[0]
            caption = self._format_content_for_platform(post.content, "instagram")

            # Upload media to Instagram
            if media_path.lower().endswith((".mp4", ".mov")):
                # Video post
                media_type = "VIDEO"
            else:
                # Image post
                media_type = "IMAGE"

            # Create container
            container_url = f"https://graph.facebook.com/v18.0/{
                config['business_account_id']
            }/media"
            container_params = {
                "image_url": media_path if media_path.startswith("http") else None,
                "caption": caption,
                "access_token": config["access_token"],
            }

            container_response = requests.post(container_url, params=container_params)
            container_data = container_response.json()

            if "id" not in container_data:
                raise Exception(f"Container creation failed: {container_data}")

            # Publish container
            publish_url = f"https://graph.facebook.com/v18.0/{
                config['business_account_id']
            }/media_publish"
            publish_params = {
                "creation_id": container_data["id"],
                "access_token": config["access_token"],
            }

            publish_response = requests.post(publish_url, params=publish_params)
            publish_data = publish_response.json()

            return {
                "success": True,
                "media_id": publish_data.get("id"),
                "url": f"https://instagram.com/p/{publish_data.get('id')}",
            }

        except Exception as e:
            raise Exception(f"Instagram posting failed: {e}")

    async def _post_to_linkedin(self, post: SocialPost) -> dict:
        """Post to LinkedIn using LinkedIn API"""
        config = self.platforms["linkedin"]

        try:
            headers = {
                "Authorization": f"Bearer {config['access_token']}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            }

            # Create post payload
            payload = {
                "author": f"urn:li:organization:{config['organization_id']}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": self._format_content_for_platform(
                                post.content,
                                "linkedin",
                            ),
                        },
                        "shareMediaCategory": "NONE",
                    },
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }

            # Add media if available
            if post.media_paths:
                payload["specificContent"]["com.linkedin.ugc.ShareContent"][
                    "shareMediaCategory"
                ] = "IMAGE"
                # LinkedIn media upload is complex - simplified for now

            response = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json=payload,
            )

            if response.status_code == 201:
                return {
                    "success": True,
                    "post_id": response.json().get("id"),
                    "url": "https://linkedin.com",  # LinkedIn doesn't provide direct URLs
                }
            raise Exception(
                f"LinkedIn API error: {response.status_code} - {response.text}",
            )

        except Exception as e:
            raise Exception(f"LinkedIn posting failed: {e}")

    def _format_content_for_platform(self, content: str, platform: str) -> str:
        """Format content according to platform-specific requirements"""
        if platform == "twitter":
            # Add hashtags if they fit
            if len(content) < 250 and hasattr(self, "default_hashtags"):
                content += " " + " ".join(self.default_hashtags["twitter"])
            return content[:280]  # Twitter character limit

        if platform == "instagram":
            # Instagram allows longer captions and more hashtags
            if hasattr(self, "default_hashtags"):
                content += "\n\n" + " ".join(self.default_hashtags["instagram"])
            return content[:2200]  # Instagram caption limit

        if platform == "linkedin":
            # Professional tone for LinkedIn
            if hasattr(self, "default_hashtags"):
                content += "\n\n" + " ".join(self.default_hashtags["linkedin"])
            return content[:3000]  # LinkedIn post limit

        if platform == "reddit":
            # Reddit formatting with markdown support
            return content

        return content

    def _split_into_tweets(self, content: str) -> list[str]:
        """Split long content into tweet-sized chunks"""
        tweets = []
        words = content.split()
        current_tweet = ""
        tweet_number = 1
        total_tweets = (len(content) // 250) + 1

        for word in words:
            thread_indicator = f" ({tweet_number}/{total_tweets})"
            test_tweet = current_tweet + " " + word + thread_indicator

            if len(test_tweet) <= 280:
                current_tweet += " " + word if current_tweet else word
            else:
                tweets.append(current_tweet + f" ({tweet_number}/{total_tweets})")
                current_tweet = word
                tweet_number += 1

        if current_tweet:
            tweets.append(current_tweet + f" ({tweet_number}/{total_tweets})")

        return tweets

    def schedule_post(self, post: SocialPost, scheduled_time: datetime = None):
        """Schedule a post for later publication"""
        if scheduled_time:
            post.scheduled_time = scheduled_time

        schedule.every().day.at(scheduled_time.strftime("%H:%M")).do(
            self._execute_scheduled_post,
            post,
        ).tag(f"scheduled_post_{int(time.time())}")

    def _execute_scheduled_post(self, post: SocialPost):
        """Execute a scheduled post"""
        asyncio.run(self.post_to_all_platforms(post))

    def get_optimal_posting_times(self, platform: str = None) -> dict:
        """Get optimal posting times for platforms"""
        if platform:
            return {platform: self.posting_schedule.get(platform, [])}
        return self.posting_schedule

    def get_analytics_summary(self) -> dict:
        """Get posting analytics summary"""
        return {
            "total_posts": len(self.analytics),
            "successful_posts": len(
                [p for p in self.analytics.values() if p.get("success")],
            ),
            "failed_posts": len(
                [p for p in self.analytics.values() if not p.get("success")],
            ),
            "platforms_used": list(
                set([p.get("platform") for p in self.analytics.values()]),
            ),
            "last_post_time": (
                max([p.get("timestamp") for p in self.analytics.values()])
                if self.analytics
                else None
            ),
        }

    def run_scheduler(self):
        """Run the post scheduler"""
        self.logger.info("Starting social media scheduler...")
        while True:
            schedule.run_pending()
            time.sleep(60)


# Utility functions


def create_sample_post() -> SocialPost:
    """Create a sample social media post for testing"""
    return SocialPost(
        content="🚀 Excited to share our latest automation breakthrough! The new social media distribution system is live and helping teams save hours of manual posting. #automation #socialmedia #productivity",
        platforms=["twitter", "linkedin"],
        hashtags=["#automation", "#socialmedia", "#productivity"],
        metadata={
            "title": "New Automation Breakthrough",
            "subreddits": ["automation", "productivity"],
        },
    )


def main():
    """Main function for testing"""
    distributor = SocialMediaDistributor()

    # Create and post a sample
    sample_post = create_sample_post()

    # Post immediately
    results = asyncio.run(distributor.post_to_all_platforms(sample_post))
    print("Posting results:", json.dumps(results, indent=2, default=str))

    # Show analytics
    print("Analytics:", distributor.get_analytics_summary())


if __name__ == "__main__":
    main()
