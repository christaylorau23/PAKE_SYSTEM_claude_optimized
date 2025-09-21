"""APIConfig - Centralized API configuration and key management

Secure configuration management for all external API integrations.
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any


class APIProvider(Enum):
    """Supported API providers"""

    GOOGLE_TRENDS = "google_trends"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    TIKTOK = "tiktok"


@dataclass
class APIEndpoint:
    """API endpoint configuration"""

    base_url: str
    version: str
    requires_auth: bool
    auth_type: str  # 'api_key', 'oauth', 'bearer_token'
    rate_limit_tier: str


class APIConfig:
    """Centralized API configuration management

    Features:
    - Secure credential management
    - Environment-based configuration
    - API endpoint management
    - Authentication handling
    - Configuration validation
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._load_configuration()

    def _load_configuration(self):
        """Load API configurations from environment variables"""
        # Google Trends API Configuration
        self.google_trends = {
            "enabled": os.getenv("GOOGLE_TRENDS_ENABLED", "true").lower() == "true",
            "base_url": "https://trends.google.com",
            "requires_auth": False,
            "rate_limit_tier": "free",
            "endpoints": {
                "trending_searches": "/trending/rss",
                "interest_over_time": "/api/widgetdata/multiline",
                "related_queries": "/api/widgetdata/relatedsearches",
            },
        }

        # YouTube Data API v3 Configuration
        self.youtube = {
            "enabled": os.getenv("YOUTUBE_API_ENABLED", "true").lower() == "true",
            "api_key": os.getenv("YOUTUBE_API_KEY"),
            "base_url": "https://www.googleapis.com/youtube/v3",
            "requires_auth": True,
            "auth_type": "api_key",
            "rate_limit_tier": "standard",
            "endpoints": {
                "trending_videos": "/videos",
                "search": "/search",
                "video_details": "/videos",
                "channel_details": "/channels",
            },
            "quota_limit": 10000,  # Daily quota units
        }

        # Twitter API v2 Configuration
        self.twitter = {
            "enabled": os.getenv("TWITTER_API_ENABLED", "true").lower() == "true",
            "api_key": os.getenv("TWITTER_API_KEY"),
            "api_secret": os.getenv("TWITTER_API_SECRET"),
            "bearer_token": os.getenv("TWITTER_BEARER_TOKEN"),
            "access_token": os.getenv("TWITTER_ACCESS_TOKEN"),
            "access_token_secret": os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
            "base_url": "https://api.twitter.com/2",
            "requires_auth": True,
            "auth_type": "bearer_token",
            "rate_limit_tier": "essential",
            "endpoints": {
                "trending_topics": "/trends/place",
                "tweet_search": "/tweets/search/recent",
                "user_timeline": "/users/{id}/tweets",
                "tweet_counts": "/tweets/counts/recent",
            },
        }

        # TikTok Research API Configuration
        self.tiktok = {
            "enabled": os.getenv("TIKTOK_API_ENABLED", "true").lower() == "true",
            "api_key": os.getenv("TIKTOK_API_KEY"),
            "api_secret": os.getenv("TIKTOK_API_SECRET"),
            "base_url": "https://research-api.tiktok.com/v1",
            "requires_auth": True,
            "auth_type": "api_key",
            "rate_limit_tier": "research",
            "endpoints": {
                "video_search": "/video/search",
                "trending_hashtags": "/hashtag/trending",
                "video_details": "/video/info",
                "user_details": "/user/info",
            },
        }

        # Common configuration
        self.common = {
            "request_timeout": int(os.getenv("API_REQUEST_TIMEOUT", "30")),
            "retry_attempts": int(os.getenv("API_RETRY_ATTEMPTS", "3")),
            "retry_backoff": float(os.getenv("API_RETRY_BACKOFF", "1.0")),
            "user_agent": os.getenv("API_USER_AGENT", "PAKE-TrendSystem/1.0"),
            "ssl_verify": os.getenv("API_SSL_VERIFY", "true").lower() == "true",
        }

        self._validate_configuration()

    def _validate_configuration(self):
        """Validate API configurations"""
        issues = []

        # Check YouTube API key
        if self.youtube["enabled"] and not self.youtube["api_key"]:
            issues.append("YouTube API enabled but YOUTUBE_API_KEY not set")

        # Check Twitter credentials
        if self.twitter["enabled"]:
            if not self.twitter["bearer_token"]:
                issues.append("Twitter API enabled but TWITTER_BEARER_TOKEN not set")

        # Check TikTok credentials
        if self.tiktok["enabled"]:
            if not self.tiktok["api_key"]:
                issues.append("TikTok API enabled but TIKTOK_API_KEY not set")

        if issues:
            for issue in issues:
                self.logger.warning(f"Configuration issue: {issue}")

    def get_api_config(self, provider: APIProvider) -> dict[str, Any]:
        """Get configuration for specific API provider"""
        config_map = {
            APIProvider.GOOGLE_TRENDS: self.google_trends,
            APIProvider.YOUTUBE: self.youtube,
            APIProvider.TWITTER: self.twitter,
            APIProvider.TIKTOK: self.tiktok,
        }

        return config_map.get(provider, {})

    def is_api_enabled(self, provider: APIProvider) -> bool:
        """Check if API provider is enabled"""
        config = self.get_api_config(provider)
        return config.get("enabled", False)

    def get_auth_headers(self, provider: APIProvider) -> dict[str, str]:
        """Get authentication headers for API provider"""
        config = self.get_api_config(provider)

        if not config.get("requires_auth", False):
            return {}

        auth_type = config.get("auth_type")
        headers = {"User-Agent": self.common["user_agent"]}

        if auth_type == "api_key":
            if provider == APIProvider.YOUTUBE:
                # YouTube uses API key as query parameter, not header
                return headers
            if provider == APIProvider.TIKTOK:
                headers["X-API-Key"] = config.get("api_key", "")
            elif provider == APIProvider.TWITTER:
                headers["Authorization"] = f"Bearer {config.get('bearer_token', '')}"

        elif auth_type == "bearer_token":
            if provider == APIProvider.TWITTER:
                headers["Authorization"] = f"Bearer {config.get('bearer_token', '')}"

        return headers

    def get_auth_params(self, provider: APIProvider) -> dict[str, str]:
        """Get authentication parameters for API provider"""
        config = self.get_api_config(provider)

        if not config.get("requires_auth", False):
            return {}

        params = {}

        if provider == APIProvider.YOUTUBE:
            params["key"] = config.get("api_key", "")

        return params

    def get_endpoint_url(
        self,
        provider: APIProvider,
        endpoint_name: str,
    ) -> str | None:
        """Get full URL for specific endpoint"""
        config = self.get_api_config(provider)

        if not config:
            return None

        base_url = config.get("base_url", "")
        endpoints = config.get("endpoints", {})
        endpoint_path = endpoints.get(endpoint_name)

        if not endpoint_path:
            return None

        return f"{base_url}{endpoint_path}"

    def get_rate_limit_info(self, provider: APIProvider) -> dict[str, Any]:
        """Get rate limit information for API provider"""
        # This would typically be loaded from a configuration file or database
        rate_limits = {
            APIProvider.GOOGLE_TRENDS: {
                "requests_per_minute": 10,
                "requests_per_hour": 500,
                "requests_per_day": 5000,
                "quota_cost_per_request": 0,
            },
            APIProvider.YOUTUBE: {
                "requests_per_minute": 100,
                "requests_per_hour": 1000,
                "requests_per_day": 10000,
                "quota_cost_per_request": 1,
            },
            APIProvider.TWITTER: {
                "requests_per_minute": 50,
                "requests_per_hour": 1500,
                "requests_per_day": 10000,
                "quota_cost_per_request": 1,
            },
            APIProvider.TIKTOK: {
                "requests_per_minute": 20,
                "requests_per_hour": 800,
                "requests_per_day": 5000,
                "quota_cost_per_request": 1,
            },
        }

        return rate_limits.get(provider, {})

    def get_all_enabled_providers(self) -> list[APIProvider]:
        """Get list of all enabled API providers"""
        enabled = []
        for provider in APIProvider:
            if self.is_api_enabled(provider):
                enabled.append(provider)
        return enabled

    def validate_provider_credentials(self, provider: APIProvider) -> bool:
        """Validate that required credentials are present for provider"""
        config = self.get_api_config(provider)

        if not config.get("enabled", False):
            return True  # Not enabled, so credentials not required

        if not config.get("requires_auth", False):
            return True  # No auth required

        auth_type = config.get("auth_type")

        if provider == APIProvider.YOUTUBE:
            return bool(config.get("api_key"))

        if provider == APIProvider.TWITTER:
            return bool(config.get("bearer_token"))

        if provider == APIProvider.TIKTOK:
            return bool(config.get("api_key") and config.get("api_secret"))

        return False

    def get_configuration_summary(self) -> dict[str, Any]:
        """Get summary of all API configurations"""
        summary = {
            "enabled_providers": [],
            "configuration_issues": [],
            "total_daily_quota": 0,
        }

        for provider in APIProvider:
            config = self.get_api_config(provider)
            if config.get("enabled", False):
                summary["enabled_providers"].append(provider.value)

                # Check for issues
                if not self.validate_provider_credentials(provider):
                    summary["configuration_issues"].append(
                        f"{provider.value}: Missing required credentials",
                    )

                # Add to quota
                rate_info = self.get_rate_limit_info(provider)
                summary["total_daily_quota"] += rate_info.get("requests_per_day", 0)

        return summary

    def reload_configuration(self):
        """Reload configuration from environment variables"""
        self.logger.info("Reloading API configuration...")
        self._load_configuration()

    def set_api_enabled(self, provider: APIProvider, enabled: bool):
        """Enable or disable an API provider"""
        config = self.get_api_config(provider)
        if config:
            config["enabled"] = enabled
            self.logger.info(
                f"{provider.value} API {'enabled' if enabled else 'disabled'}",
            )

    def update_credentials(self, provider: APIProvider, credentials: dict[str, str]):
        """Update credentials for an API provider"""
        config = self.get_api_config(provider)
        if not config:
            return False

        for key, value in credentials.items():
            if key in config:
                config[key] = value

        # Re-validate after update
        if self.validate_provider_credentials(provider):
            self.logger.info(f"Updated credentials for {provider.value}")
            return True
        self.logger.error(f"Invalid credentials for {provider.value}")
        return False
