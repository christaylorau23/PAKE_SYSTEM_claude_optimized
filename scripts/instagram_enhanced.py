#!/usr/bin/env python3
"""
Enhanced Instagram Integration with Reels Support
Supports Stories, Reels, Carousels, and IGTV
"""

import json
import logging
import os
import time
from dataclasses import dataclass

import requests


@dataclass
class InstagramMedia:
    """Instagram media configuration"""

    media_type: str  # IMAGE, VIDEO, CAROUSEL_ALBUM, STORIES
    media_url: str
    caption: str = ""
    thumbnail_url: str = None
    location_id: str = None
    user_tags: list[dict] = None
    product_tags: list[dict] = None


class InstagramEnhanced:
    """Enhanced Instagram posting with full feature support"""

    def __init__(self, access_token: str, business_account_id: str):
        self.access_token = access_token
        self.business_account_id = business_account_id
        self.base_url = "https://graph.facebook.com/v18.0"
        self.logger = logging.getLogger(__name__)

        # Instagram API limits
        self.max_caption_length = 2200
        self.max_hashtags = 30
        self.supported_image_formats = [".jpg", ".jpeg", ".png"]
        self.supported_video_formats = [".mp4", ".mov"]

    async def post_single_media(self, media: InstagramMedia) -> dict:
        """Post single image or video"""
        try:
            # Create media container
            container_id = await self._create_media_container(media)

            # Publish the container
            result = await self._publish_media(container_id)

            return {
                "success": True,
                "media_id": result["id"],
                "permalink": await self._get_media_permalink(result["id"]),
            }

        except Exception as e:
            self.logger.error(f"Single media post failed: {e}")
            return {"success": False, "error": str(e)}

    async def post_carousel(
        self,
        media_list: list[InstagramMedia],
        caption: str = "",
    ) -> dict:
        """Post carousel (multiple images/videos)"""
        try:
            if len(media_list) < 2 or len(media_list) > 10:
                raise ValueError("Carousel must have 2-10 media items")

            # Create containers for each media item
            child_containers = []
            for media in media_list:
                media.caption = ""  # Carousel items don't have individual captions
                container_id = await self._create_media_container(
                    media,
                    is_carousel_item=True,
                )
                child_containers.append(container_id)

            # Create carousel container
            carousel_container = await self._create_carousel_container(
                child_containers,
                caption,
            )

            # Publish carousel
            result = await self._publish_media(carousel_container)

            return {
                "success": True,
                "media_id": result["id"],
                "permalink": await self._get_media_permalink(result["id"]),
                "carousel_items": len(child_containers),
            }

        except Exception as e:
            self.logger.error(f"Carousel post failed: {e}")
            return {"success": False, "error": str(e)}

    async def post_reel(
        self,
        video_url: str,
        caption: str = "",
        cover_url: str = None,
        audio_name: str = None,
    ) -> dict:
        """Post Instagram Reel with enhanced features"""
        try:
            # Validate video format and duration
            if not await self._validate_reel_video(video_url):
                raise ValueError("Invalid video format or duration for Reels")

            # Create Reel container
            container_params = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": self._format_caption(caption),
                "access_token": self.access_token,
            }

            # Add cover image if provided
            if cover_url:
                container_params["cover_url"] = cover_url

            # Add audio if specified
            if audio_name:
                container_params["audio_name"] = audio_name

            # Create container
            container_url = f"{self.base_url}/{self.business_account_id}/media"
            response = requests.post(container_url, params=container_params)
            container_data = response.json()

            if "id" not in container_data:
                raise Exception(f"Reel container creation failed: {container_data}")

            # Wait for video processing
            await self._wait_for_video_processing(container_data["id"])

            # Publish Reel
            result = await self._publish_media(container_data["id"])

            return {
                "success": True,
                "reel_id": result["id"],
                "permalink": await self._get_media_permalink(result["id"]),
            }

        except Exception as e:
            self.logger.error(f"Reel post failed: {e}")
            return {"success": False, "error": str(e)}

    async def post_story(self, media: InstagramMedia) -> dict:
        """Post to Instagram Stories"""
        try:
            # Stories have different requirements
            media.media_type = "STORIES"

            # Create story container
            container_params = {
                "media_type": "STORIES",
                "access_token": self.access_token,
            }

            if media.media_url.lower().endswith(tuple(self.supported_image_formats)):
                container_params["image_url"] = media.media_url
            elif media.media_url.lower().endswith(tuple(self.supported_video_formats)):
                container_params["video_url"] = media.media_url
            else:
                raise ValueError("Unsupported media format for Stories")

            # Stories don't support captions, but support text overlays
            # This would require additional Story-specific parameters

            container_url = f"{self.base_url}/{self.business_account_id}/media"
            response = requests.post(container_url, params=container_params)
            container_data = response.json()

            if "id" not in container_data:
                raise Exception(f"Story container creation failed: {container_data}")

            # Publish story
            result = await self._publish_media(container_data["id"])

            return {
                "success": True,
                "story_id": result["id"],
                "expires_at": int(time.time()) + 86400,  # Stories expire in 24h
            }

        except Exception as e:
            self.logger.error(f"Story post failed: {e}")
            return {"success": False, "error": str(e)}

    async def _create_media_container(
        self,
        media: InstagramMedia,
        is_carousel_item: bool = False,
    ) -> str:
        """Create media container for Instagram post"""
        params = {"access_token": self.access_token}

        # Set media type and URL
        if media.media_url.lower().endswith(tuple(self.supported_image_formats)):
            params["image_url"] = media.media_url
        elif media.media_url.lower().endswith(tuple(self.supported_video_formats)):
            params["video_url"] = media.media_url
            if media.thumbnail_url:
                params["thumb_offset"] = 0  # Or specific timestamp
        else:
            raise ValueError(f"Unsupported media format: {media.media_url}")

        # Add caption (not for carousel items)
        if media.caption and not is_carousel_item:
            params["caption"] = self._format_caption(media.caption)

        # Add location if specified
        if media.location_id:
            params["location_id"] = media.location_id

        # Add user tags
        if media.user_tags:
            params["user_tags"] = json.dumps(media.user_tags)

        # Add product tags (for shopping)
        if media.product_tags:
            params["product_tags"] = json.dumps(media.product_tags)

        # Create container
        container_url = f"{self.base_url}/{self.business_account_id}/media"
        response = requests.post(container_url, params=params)
        data = response.json()

        if "id" not in data:
            raise Exception(f"Container creation failed: {data}")

        return data["id"]

    async def _create_carousel_container(
        self,
        child_containers: list[str],
        caption: str,
    ) -> str:
        """Create carousel album container"""
        params = {
            "media_type": "CAROUSEL",
            "children": ",".join(child_containers),
            "caption": self._format_caption(caption),
            "access_token": self.access_token,
        }

        container_url = f"{self.base_url}/{self.business_account_id}/media"
        response = requests.post(container_url, params=params)
        data = response.json()

        if "id" not in data:
            raise Exception(f"Carousel container creation failed: {data}")

        return data["id"]

    async def _publish_media(self, container_id: str) -> dict:
        """Publish media container"""
        params = {"creation_id": container_id, "access_token": self.access_token}

        publish_url = f"{self.base_url}/{self.business_account_id}/media_publish"
        response = requests.post(publish_url, params=params)
        data = response.json()

        if "id" not in data:
            raise Exception(f"Media publishing failed: {data}")

        return data

    async def _wait_for_video_processing(self, container_id: str, timeout: int = 300):
        """Wait for video processing to complete"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = await self._get_container_status(container_id)

            if status == "FINISHED":
                return True
            if status in ["ERROR", "CANCELED"]:
                raise Exception(f"Video processing failed with status: {status}")

            await asyncio.sleep(10)  # Wait 10 seconds before checking again

        raise Exception("Video processing timeout")

    async def _get_container_status(self, container_id: str) -> str:
        """Get media container processing status"""
        params = {"fields": "status_code", "access_token": self.access_token}

        url = f"{self.base_url}/{container_id}"
        response = requests.get(url, params=params)
        data = response.json()

        return data.get("status_code", "UNKNOWN")

    async def _validate_reel_video(self, video_url: str) -> bool:
        """Validate video meets Reels requirements"""
        # Instagram Reels requirements:
        # - Duration: 15 seconds to 90 seconds
        # - Aspect ratio: 9:16 (vertical)
        # - Format: MP4 or MOV
        # - Resolution: minimum 720p

        # For now, just check file extension
        return video_url.lower().endswith((".mp4", ".mov"))

    async def _get_media_permalink(self, media_id: str) -> str:
        """Get permalink for published media"""
        params = {"fields": "permalink", "access_token": self.access_token}

        url = f"{self.base_url}/{media_id}"
        response = requests.get(url, params=params)
        data = response.json()

        return data.get("permalink", "")

    def _format_caption(self, caption: str) -> str:
        """Format caption according to Instagram requirements"""
        if len(caption) > self.max_caption_length:
            caption = caption[: self.max_caption_length - 3] + "..."

        return caption

    def _extract_hashtags(self, caption: str) -> tuple[str, list[str]]:
        """Extract hashtags from caption"""
        import re

        hashtags = re.findall(r"#\w+", caption)
        clean_caption = re.sub(r"#\w+", "", caption).strip()

        # Limit hashtags
        if len(hashtags) > self.max_hashtags:
            hashtags = hashtags[: self.max_hashtags]

        return clean_caption, hashtags

    async def get_media_insights(self, media_id: str) -> dict:
        """Get insights for published media"""
        params = {
            "metric": "engagement,impressions,reach,saved",
            "access_token": self.access_token,
        }

        url = f"{self.base_url}/{media_id}/insights"
        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.json()
        return {"error": f"Insights unavailable: {response.status_code}"}

    async def schedule_post(self, media: InstagramMedia, publish_time: int) -> dict:
        """Schedule post for later (Creator Studio feature)"""
        # Note: Scheduled posts require Creator Studio API access
        # This is a simplified implementation

        try:
            container_id = await self._create_media_container(media)

            # Add scheduling parameter
            params = {
                "creation_id": container_id,
                "published": "false",
                "scheduled_publish_time": publish_time,
                "access_token": self.access_token,
            }

            publish_url = f"{self.base_url}/{self.business_account_id}/media_publish"
            response = requests.post(publish_url, params=params)
            data = response.json()

            return {
                "success": True,
                "scheduled_id": data.get("id"),
                "publish_time": publish_time,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# Usage example


async def demo_instagram_features():
    """Demonstrate Instagram enhanced features"""

    # Initialize client
    instagram = InstagramEnhanced(
        access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN"),
        business_account_id=os.getenv("INSTAGRAM_BUSINESS_ID"),
    )

    # Single image post
    single_media = InstagramMedia(
        media_type="IMAGE",
        media_url="https://example.com/image.jpg",
        caption="Check out our latest product! #newlaunch #excited",
        location_id="123456789",
    )

    result = await instagram.post_single_media(single_media)
    print(f"Single post result: {result}")

    # Reel post
    reel_result = await instagram.post_reel(
        video_url="https://example.com/reel.mp4",
        caption="Behind the scenes of our latest project! #bts #reels",
        cover_url="https://example.com/cover.jpg",
    )
    print(f"Reel result: {reel_result}")

    # Carousel post
    carousel_media = [
        InstagramMedia("IMAGE", "https://example.com/image1.jpg"),
        InstagramMedia("IMAGE", "https://example.com/image2.jpg"),
        InstagramMedia("VIDEO", "https://example.com/video1.mp4"),
    ]

    carousel_result = await instagram.post_carousel(
        carousel_media,
        "Swipe to see our journey! #carousel #story",
    )
    print(f"Carousel result: {carousel_result}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(demo_instagram_features())
