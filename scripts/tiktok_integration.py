#!/usr/bin/env python3
"""
TikTok Business API Integration
Video upload, posting, and management for TikTok content
"""

import json
import logging
import os
import time
from dataclasses import dataclass

import requests


@dataclass
class TikTokVideo:
    """TikTok video data structure"""

    video_path: str
    title: str
    description: str = ""
    hashtags: list[str] = None
    # PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, SELF_ONLY
    privacy_level: str = "PUBLIC_TO_EVERYONE"
    disable_duet: bool = False
    disable_comment: bool = False
    disable_stitch: bool = False
    video_cover_timestamp_ms: int = 1000


class TikTokIntegration:
    """TikTok Business API integration for content posting"""

    def __init__(self, client_key: str, client_secret: str, access_token: str):
        self.client_key = client_key
        self.client_secret = client_secret
        self.access_token = access_token
        self.base_url = "https://business-api.tiktok.com"
        self.open_api_url = "https://open-api.tiktok.com"
        self.logger = logging.getLogger(__name__)

        # TikTok API limits and requirements
        self.max_title_length = 150
        self.max_description_length = 2200
        self.max_hashtags = 100
        self.supported_video_formats = [".mp4", ".mov", ".webm"]
        self.max_video_size = 128 * 1024 * 1024  # 128MB
        self.min_duration = 3  # 3 seconds
        self.max_duration = 180  # 3 minutes

    async def upload_video(self, video: TikTokVideo) -> dict:
        """Upload video to TikTok"""
        try:
            # Step 1: Initialize video upload
            init_response = await self._initialize_video_upload()

            if not init_response.get("success"):
                return init_response

            upload_url = init_response["upload_url"]
            video_id = init_response["video_id"]

            # Step 2: Upload video file
            upload_response = await self._upload_video_file(
                upload_url,
                video.video_path,
            )

            if not upload_response.get("success"):
                return upload_response

            # Step 3: Publish video with metadata
            publish_response = await self._publish_video(video_id, video)

            return publish_response

        except Exception as e:
            self.logger.error(f"TikTok video upload failed: {e}")
            return {"success": False, "error": str(e)}

    async def _initialize_video_upload(self) -> dict:
        """Initialize video upload process"""
        try:
            endpoint = "/v2/post/publish/video/init/"
            url = self.open_api_url + endpoint

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            # Create request body
            body = {
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": (
                        os.path.getsize(video.video_path)
                        if hasattr(self, "current_video_path")
                        else 0
                    ),
                },
            }

            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if data.get("error", {}).get("code") == "ok":
                return {
                    "success": True,
                    "upload_url": data["data"]["upload_url"],
                    "video_id": data["data"]["publish_id"],
                }
            return {
                "success": False,
                "error": data.get("error", {}).get(
                    "message",
                    "Upload initialization failed",
                ),
            }

        except Exception as e:
            return {"success": False, "error": f"Initialization failed: {str(e)}"}

    async def _upload_video_file(self, upload_url: str, video_path: str) -> dict:
        """Upload video file to TikTok servers"""
        try:
            if not os.path.exists(video_path):
                return {"success": False, "error": "Video file not found"}

            # Validate video file
            validation = self._validate_video_file(video_path)
            if not validation["valid"]:
                return {"success": False, "error": validation["error"]}

            # Upload file in chunks for large files
            with open(video_path, "rb") as video_file:
                files = {"video": video_file}

                response = requests.put(
                    upload_url,
                    files=files,
                    timeout=300,  # 5 minute timeout for video upload
                )

                if response.status_code == 200:
                    return {"success": True}
                return {
                    "success": False,
                    "error": f"Upload failed with status: {response.status_code}",
                }

        except Exception as e:
            return {"success": False, "error": f"File upload failed: {str(e)}"}

    async def _publish_video(self, video_id: str, video: TikTokVideo) -> dict:
        """Publish video with metadata"""
        try:
            endpoint = "/v2/post/publish/video/"
            url = self.open_api_url + endpoint

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            # Prepare video metadata
            body = {
                "post_info": {
                    "title": video.title[: self.max_title_length],
                    "privacy_level": video.privacy_level,
                    "disable_duet": video.disable_duet,
                    "disable_comment": video.disable_comment,
                    "disable_stitch": video.disable_stitch,
                    "video_cover_timestamp_ms": video.video_cover_timestamp_ms,
                },
                "source_info": {"publish_id": video_id},
            }

            # Add description if provided
            if video.description:
                body["post_info"]["description"] = video.description[
                    : self.max_description_length
                ]

            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if data.get("error", {}).get("code") == "ok":
                return {
                    "success": True,
                    "video_id": data["data"]["publish_id"],
                    "share_url": data["data"].get("share_url", ""),
                    "embed_url": data["data"].get("embed_url", ""),
                }
            return {
                "success": False,
                "error": data.get("error", {}).get(
                    "message",
                    "Video publish failed",
                ),
            }

        except Exception as e:
            return {"success": False, "error": f"Publish failed: {str(e)}"}

    def _validate_video_file(self, video_path: str) -> dict:
        """Validate video file meets TikTok requirements"""
        try:
            # Check file exists
            if not os.path.exists(video_path):
                return {"valid": False, "error": "Video file not found"}

            # Check file size
            file_size = os.path.getsize(video_path)
            if file_size > self.max_video_size:
                return {
                    "valid": False,
                    "error": f"Video too large: {file_size} bytes (max: {
                        self.max_video_size
                    })",
                }

            # Check file format
            file_extension = os.path.splitext(video_path)[1].lower()
            if file_extension not in self.supported_video_formats:
                return {
                    "valid": False,
                    "error": f"Unsupported format: {file_extension}",
                }

            # TODO: Add video duration check using ffprobe or similar
            # For now, assume it's valid if format and size are correct

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    async def get_user_info(self) -> dict:
        """Get TikTok user information"""
        try:
            endpoint = "/v2/user/info/"
            url = self.open_api_url + endpoint

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            params = {
                "fields": "open_id,union_id,avatar_url,display_name,bio_description,profile_deep_link,is_verified,follower_count,following_count,likes_count,video_count",
            }

            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            if data.get("error", {}).get("code") == "ok":
                return {"success": True, "user_info": data["data"]["user"]}
            return {
                "success": False,
                "error": data.get("error", {}).get(
                    "message",
                    "Failed to get user info",
                ),
            }

        except Exception as e:
            return {"success": False, "error": f"User info request failed: {str(e)}"}

    async def get_video_list(self, cursor: int = 0, max_count: int = 20) -> dict:
        """Get list of user's videos"""
        try:
            endpoint = "/v2/video/list/"
            url = self.open_api_url + endpoint

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            body = {
                "max_count": min(max_count, 20),  # API limits to 20
                "cursor": cursor,
                "fields": "id,title,video_description,duration,cover_image_url,share_url,embed_url,view_count,like_count,comment_count,share_count,create_time",
            }

            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if data.get("error", {}).get("code") == "ok":
                return {
                    "success": True,
                    "videos": data["data"]["videos"],
                    "cursor": data["data"].get("cursor", 0),
                    "has_more": data["data"].get("has_more", False),
                }
            return {
                "success": False,
                "error": data.get("error", {}).get(
                    "message",
                    "Failed to get video list",
                ),
            }

        except Exception as e:
            return {"success": False, "error": f"Video list request failed: {str(e)}"}

    async def get_video_analytics(self, video_id: str) -> dict:
        """Get analytics for a specific video"""
        try:
            endpoint = "/v2/video/insights/"
            url = self.open_api_url + endpoint

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            body = {
                "video_ids": [video_id],
                "fields": "views,profile_views,likes,comments,shares,reach,video_views_by_country,video_views_by_age_group,video_views_by_gender",
            }

            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if data.get("error", {}).get("code") == "ok":
                return {
                    "success": True,
                    "analytics": (
                        data["data"]["videos"][0] if data["data"]["videos"] else {}
                    ),
                }
            return {
                "success": False,
                "error": data.get("error", {}).get(
                    "message",
                    "Failed to get video analytics",
                ),
            }

        except Exception as e:
            return {"success": False, "error": f"Analytics request failed: {str(e)}"}

    def _format_hashtags(self, hashtags: list[str]) -> str:
        """Format hashtags for TikTok"""
        if not hashtags:
            return ""

        # Ensure hashtags start with #
        formatted = []
        for tag in hashtags[: self.max_hashtags]:
            if not tag.startswith("#"):
                tag = "#" + tag
            formatted.append(tag)

        return " ".join(formatted)

    async def schedule_video(self, video: TikTokVideo, schedule_time: int) -> dict:
        """Schedule video for future posting"""
        # Note: TikTok's scheduling feature may be limited
        # This is a conceptual implementation
        try:
            # For now, we'll store the scheduled video locally
            # In a real implementation, you'd use a job scheduler

            scheduled_post = {
                "video": video.__dict__,
                "schedule_time": schedule_time,
                "status": "scheduled",
                "created_at": int(time.time()),
            }

            # Save to local scheduler (you'd use Redis/database in production)
            schedule_file = "tiktok_scheduled_posts.json"

            scheduled_posts = []
            if os.path.exists(schedule_file):
                with open(schedule_file) as f:
                    scheduled_posts = json.load(f)

            scheduled_posts.append(scheduled_post)

            with open(schedule_file, "w") as f:
                json.dump(scheduled_posts, f, indent=2)

            return {
                "success": True,
                "scheduled_id": f"tiktok_{int(time.time())}",
                "schedule_time": schedule_time,
            }

        except Exception as e:
            return {"success": False, "error": f"Scheduling failed: {str(e)}"}


class TikTokHashtagGenerator:
    """Generate trending hashtags for TikTok content"""

    def __init__(self, client_key: str, access_token: str):
        self.client_key = client_key
        self.access_token = access_token
        self.open_api_url = "https://open-api.tiktok.com"

    async def get_trending_hashtags(self, count: int = 20) -> dict:
        """Get trending hashtags"""
        try:
            endpoint = "/v2/research/hashtag/trending/"
            url = self.open_api_url + endpoint

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            body = {
                "count": min(count, 50),
                "region_code": "US",  # Can be made configurable
                "period": 7,  # Last 7 days
            }

            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if data.get("error", {}).get("code") == "ok":
                return {"success": True, "hashtags": data["data"]["hashtags"]}
            return {
                "success": False,
                "error": data.get("error", {}).get(
                    "message",
                    "Failed to get trending hashtags",
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Trending hashtags request failed: {str(e)}",
            }

    def suggest_hashtags(self, content: str, industry: str = None) -> list[str]:
        """Suggest hashtags based on content"""
        # Basic hashtag suggestions based on content
        # In production, you'd use ML/AI for better suggestions

        common_hashtags = ["#fyp", "#foryou", "#viral", "#trending", "#tiktok"]

        # Industry-specific hashtags
        industry_hashtags = {
            "tech": ["#tech", "#technology", "#innovation", "#coding", "#ai"],
            "business": [
                "#business",
                "#entrepreneur",
                "#success",
                "#motivation",
                "#hustle",
            ],
            "lifestyle": ["#lifestyle", "#daily", "#life", "#mood", "#aesthetic"],
            "education": ["#education", "#learning", "#knowledge", "#study", "#tips"],
            "entertainment": ["#entertainment", "#fun", "#comedy", "#music", "#dance"],
        }

        suggestions = common_hashtags.copy()

        if industry and industry in industry_hashtags:
            suggestions.extend(industry_hashtags[industry])

        # Add content-based hashtags (simple keyword extraction)
        words = content.lower().split()
        for word in words:
            if len(word) > 3 and word.isalpha():
                suggestions.append(f"#{word}")

        # Remove duplicates and limit
        return list(set(suggestions))[:20]


# Usage example


async def demo_tiktok_integration():
    """Demonstrate TikTok integration features"""

    # Initialize TikTok client
    tiktok = TikTokIntegration(
        client_key=os.getenv("TIKTOK_CLIENT_KEY"),
        client_secret=os.getenv("TIKTOK_CLIENT_SECRET"),
        access_token=os.getenv("TIKTOK_ACCESS_TOKEN"),
    )

    # Create video post
    video = TikTokVideo(
        video_path="/path/to/video.mp4",
        title="Amazing automation in action! 🤖",
        description="Check out this incredible automation that saves hours of work every day!",
        hashtags=["#automation", "#tech", "#productivity", "#fyp"],
        privacy_level="PUBLIC_TO_EVERYONE",
    )

    # Upload and publish video
    result = await tiktok.upload_video(video)
    print(f"TikTok upload result: {result}")

    # Get user info
    user_info = await tiktok.get_user_info()
    print(f"User info: {user_info}")

    # Get video analytics (for existing video)
    if result.get("success") and result.get("video_id"):
        analytics = await tiktok.get_video_analytics(result["video_id"])
        print(f"Video analytics: {analytics}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(demo_tiktok_integration())
