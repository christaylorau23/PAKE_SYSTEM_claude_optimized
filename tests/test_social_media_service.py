#!/usr/bin/env python3
"""
PAKE System - Social Media Integration Service Tests
Phase 2B Sprint 3: Comprehensive TDD testing for multi-platform social media ingestion

Tests Twitter, LinkedIn, Reddit integration with intelligent filtering,
sentiment analysis, and cognitive assessment.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from services.ingestion.social_media_service import (
    SocialMediaConfig,
    SocialMediaPost,
    SocialMediaQuery,
    SocialMediaService,
    SocialPlatform,
)

from scripts.ingestion_pipeline import ContentItem


class TestSocialMediaService:
    """
    Comprehensive test suite for social media ingestion service.
    Tests multi-platform integration, intelligent filtering, and sentiment analysis.
    """

    @pytest.fixture()
    def twitter_config(self):
        """Twitter API configuration"""
        return SocialMediaConfig(
            platform=SocialPlatform.TWITTER,
            api_credentials={
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "access_token": "test_access_token",
                "access_token_secret": "test_access_token_secret",
            },
            rate_limit_per_hour=180,
            timeout=30,
        )

    @pytest.fixture()
    def linkedin_config(self):
        """LinkedIn API configuration"""
        return SocialMediaConfig(
            platform=SocialPlatform.LINKEDIN,
            api_credentials={
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "access_token": "test_access_token",
            },
            rate_limit_per_hour=500,
            timeout=30,
        )

    @pytest.fixture()
    def reddit_config(self):
        """Reddit API configuration"""
        return SocialMediaConfig(
            platform=SocialPlatform.REDDIT,
            api_credentials={
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "user_agent": "PAKE_System_Bot/1.0",
            },
            rate_limit_per_hour=1000,
            timeout=30,
        )

    @pytest.fixture()
    def mock_cognitive_engine(self):
        """Mock cognitive engine for quality assessment"""
        engine = Mock()
        engine.assess_content_quality = AsyncMock(return_value=0.78)
        return engine

    @pytest.fixture()
    def social_media_service(
        self,
        twitter_config,
        linkedin_config,
        reddit_config,
        mock_cognitive_engine,
    ):
        """Create social media service with all platforms"""
        return SocialMediaService(
            configs=[twitter_config, linkedin_config, reddit_config],
            cognitive_engine=mock_cognitive_engine,
        )

    @pytest.fixture()
    def twitter_service(self, twitter_config, mock_cognitive_engine):
        """Create Twitter-only service"""
        return SocialMediaService(
            configs=[twitter_config],
            cognitive_engine=mock_cognitive_engine,
        )

    # ========================================================================
    # TWITTER INTEGRATION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_search_twitter_posts_successfully(self, twitter_service):
        """
        Test: Should search Twitter posts with keyword filtering
        and return structured results with engagement metrics.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.TWITTER,
            keywords=["AI", "machine learning"],
            max_results=10,
        )

        result = await twitter_service.search_posts(query)

        # Verify search success
        assert result.success
        assert result.platform == SocialPlatform.TWITTER
        assert len(result.posts) > 0
        assert result.total_posts_found >= len(result.posts)
        assert result.execution_time > 0

        # Verify Twitter-specific post structure
        post = result.posts[0]
        assert isinstance(post, SocialMediaPost)
        assert post.platform == SocialPlatform.TWITTER
        assert post.post_id
        assert post.author.startswith("@")
        assert post.content
        assert "likes" in post.engagement_metrics
        assert "retweets" in post.engagement_metrics

    @pytest.mark.asyncio()
    async def test_should_filter_twitter_hashtags_correctly(self, twitter_service):
        """
        Test: Should filter Twitter posts by hashtags
        with case-insensitive matching.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.TWITTER,
            hashtags=["AI", "MachineLearning"],
            max_results=10,
        )

        result = await twitter_service.search_posts(query)

        # Verify hashtag filtering
        assert result.success

        for post in result.posts:
            post_hashtags_lower = [tag.lower() for tag in post.hashtags]
            query_hashtags_lower = [tag.lower() for tag in query.hashtags]

            # Should contain at least one of the requested hashtags
            assert any(
                hashtag in post_hashtags_lower for hashtag in query_hashtags_lower
            )

    @pytest.mark.asyncio()
    async def test_should_respect_twitter_retweet_exclusion(self, twitter_service):
        """
        Test: Should exclude retweets when requested
        for Twitter platform.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.TWITTER,
            keywords=["AI"],
            exclude_retweets=True,
            max_results=10,
        )

        result = await twitter_service.search_posts(query)

        # Verify no retweets
        assert result.success

        for post in result.posts:
            # Should not have original post ID (which indicates a retweet)
            assert post.original_post_id is None

    # ========================================================================
    # LINKEDIN INTEGRATION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_search_linkedin_posts_with_professional_content(
        self,
        social_media_service,
    ):
        """
        Test: Should search LinkedIn posts and prioritize
        professional content with proper engagement metrics.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.LINKEDIN,
            keywords=["AI", "innovation"],
            max_results=10,
        )

        result = await social_media_service.search_posts(query)

        # Verify LinkedIn search success
        assert result.success
        assert result.platform == SocialPlatform.LINKEDIN
        assert len(result.posts) > 0

        # Verify LinkedIn-specific characteristics
        post = result.posts[0]
        assert post.platform == SocialPlatform.LINKEDIN
        assert "linkedin.com" in post.url
        assert "likes" in post.engagement_metrics
        assert "comments" in post.engagement_metrics
        assert "shares" in post.engagement_metrics

        # LinkedIn content should be professional
        content_lower = post.content.lower()
        professional_indicators = [
            "experience",
            "insight",
            "learn",
            "team",
            "project",
            "industry",
        ]
        has_professional_content = any(
            indicator in content_lower for indicator in professional_indicators
        )
        assert (
            has_professional_content or len(post.content) > 100
        )  # Either professional or substantial

    # ========================================================================
    # REDDIT INTEGRATION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_search_reddit_posts_with_subreddit_context(
        self,
        social_media_service,
    ):
        """
        Test: Should search Reddit posts with subreddit filtering
        and maintain thread context information.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.REDDIT,
            keywords=["machine", "learning"],
            subreddits=["MachineLearning", "explainlikeimfive"],
            max_results=10,
        )

        result = await social_media_service.search_posts(query)

        # Verify Reddit search success
        assert result.success
        assert result.platform == SocialPlatform.REDDIT
        assert len(result.posts) > 0

        # Verify Reddit-specific characteristics
        post = result.posts[0]
        assert post.platform == SocialPlatform.REDDIT
        assert post.author.startswith("u/")
        assert "reddit.com" in post.url
        assert "upvotes" in post.engagement_metrics
        assert post.thread_context is not None
        assert "subreddit" in post.thread_context

        # Should match subreddit filter
        if query.subreddits:
            assert post.thread_context["subreddit"] in query.subreddits

    @pytest.mark.asyncio()
    async def test_should_handle_reddit_upvote_filtering(self, social_media_service):
        """
        Test: Should filter Reddit posts by minimum engagement
        using upvotes as the primary metric.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.REDDIT,
            keywords=["AI"],
            min_engagement=1000,  # Minimum upvotes
            max_results=5,
        )

        result = await social_media_service.search_posts(query)

        # Verify engagement filtering
        assert result.success

        for post in result.posts:
            total_engagement = sum(post.engagement_metrics.values())
            assert total_engagement >= query.min_engagement

    # ========================================================================
    # SENTIMENT ANALYSIS TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_apply_sentiment_analysis_to_posts(self, social_media_service):
        """
        Test: Should apply sentiment analysis to social media posts
        and provide meaningful sentiment scores.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.TWITTER,
            keywords=["AI"],
            max_results=5,
        )

        result = await social_media_service.search_posts(query)

        # Verify sentiment analysis application
        assert result.success
        assert result.sentiment_analysis_applied > 0

        for post in result.posts:
            # Should have sentiment score
            assert hasattr(post, "sentiment_score")
            assert -1.0 <= post.sentiment_score <= 1.0

    @pytest.mark.asyncio()
    async def test_should_detect_positive_sentiment_accurately(
        self,
        social_media_service,
    ):
        """
        Test: Should accurately detect positive sentiment in posts
        with positive language and expressions.
        """
        # Use mocking to test specific sentiment content
        with patch.object(
            social_media_service,
            "_generate_mock_twitter_posts",
        ) as mock_gen:
            mock_gen.return_value = [
                SocialMediaPost(
                    post_id="test_positive",
                    platform=SocialPlatform.TWITTER,
                    author="@test_user",
                    author_verified=True,
                    content="This is amazing! I love the new AI breakthrough. Fantastic work by the team. Excellent results!",
                    timestamp=datetime.now(UTC),
                    url="https://twitter.com/test",
                    engagement_metrics={"likes": 100, "retweets": 20},
                    hashtags=["AI"],
                    mentions=[],
                    media_urls=[],
                    language="en",
                ),
            ]

            query = SocialMediaQuery(
                platform=SocialPlatform.TWITTER,
                keywords=["AI"],
                max_results=1,
            )

            result = await social_media_service.search_posts(query)

            assert result.success
            assert len(result.posts) == 1

            post = result.posts[0]
            # Should detect positive sentiment
            assert post.sentiment_score > 0.3  # Clearly positive

    # ========================================================================
    # COGNITIVE INTEGRATION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_integrate_cognitive_quality_assessment(
        self,
        social_media_service,
    ):
        """
        Test: Should apply cognitive quality assessment to social media posts
        and incorporate quality scores into ranking.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.TWITTER,
            keywords=["AI"],
            max_results=3,
        )

        result = await social_media_service.search_posts(query)

        # Verify cognitive integration
        assert result.success
        assert result.cognitive_assessments_applied > 0

        # Verify quality scores are applied
        for post in result.posts:
            assert hasattr(post, "quality_score")
            assert 0.0 <= post.quality_score <= 1.0

        # Verify cognitive engine was called
        assert (
            social_media_service.cognitive_engine.assess_content_quality.call_count > 0
        )

    @pytest.mark.asyncio()
    async def test_should_handle_cognitive_assessment_failures_gracefully(
        self,
        social_media_service,
    ):
        """
        Test: Should continue processing when cognitive assessment fails
        and provide meaningful fallback quality scoring.
        """
        # Mock cognitive engine to fail
        social_media_service.cognitive_engine.assess_content_quality.side_effect = (
            Exception("Cognitive error")
        )

        query = SocialMediaQuery(
            platform=SocialPlatform.TWITTER,
            keywords=["AI"],
            max_results=3,
        )

        result = await social_media_service.search_posts(query)

        # Should still succeed despite cognitive failures
        assert result.success
        assert len(result.posts) > 0

        # Posts should still be processed with fallback scores
        for post in result.posts:
            assert post.quality_score == 0.0  # Fallback score

    # ========================================================================
    # CONTENT ITEM CONVERSION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_convert_social_posts_to_content_items_correctly(
        self,
        social_media_service,
    ):
        """
        Test: Should convert social media posts to standardized ContentItem format
        with comprehensive metadata preservation.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.TWITTER,
            keywords=["AI"],
            max_results=2,
        )

        result = await social_media_service.search_posts(query)
        content_items = await social_media_service.to_content_items(
            result,
            "social_ingestion_test",
        )

        # Verify conversion success
        assert len(content_items) == len(result.posts)

        for i, item in enumerate(content_items):
            post = result.posts[i]

            # Verify ContentItem structure
            assert isinstance(item, ContentItem)
            assert item.source_name == "social_ingestion_test"
            assert item.source_type == f"social_{result.platform.value}"
            assert post.author in item.title
            assert item.content == post.content
            assert item.author == post.author
            assert item.published == post.timestamp
            assert item.url == post.url

            # Verify metadata preservation
            assert item.metadata["post_id"] == post.post_id
            assert item.metadata["platform"] == result.platform.value
            assert item.metadata["author_verified"] == post.author_verified
            assert item.metadata["engagement_metrics"] == post.engagement_metrics
            assert item.metadata["sentiment_score"] == post.sentiment_score
            assert item.metadata["quality_score"] == post.quality_score

    # ========================================================================
    # MULTI-PLATFORM SUPPORT TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_support_multiple_platforms_concurrently(
        self,
        social_media_service,
    ):
        """
        Test: Should handle multiple social media platforms
        with proper configuration and rate limiting.
        """
        # Verify all platforms are configured
        assert SocialPlatform.TWITTER in social_media_service.configs
        assert SocialPlatform.LINKEDIN in social_media_service.configs
        assert SocialPlatform.REDDIT in social_media_service.configs

        # Test each platform individually
        platforms = [
            SocialPlatform.TWITTER,
            SocialPlatform.LINKEDIN,
            SocialPlatform.REDDIT,
        ]

        for platform in platforms:
            query = SocialMediaQuery(platform=platform, keywords=["AI"], max_results=3)

            result = await social_media_service.search_posts(query)
            assert result.success
            assert result.platform == platform
            assert len(result.posts) > 0

    # ========================================================================
    # ERROR HANDLING AND RESILIENCE TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_handle_unsupported_platform_gracefully(self, twitter_service):
        """
        Test: Should handle requests for unconfigured platforms
        with proper error reporting.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.LINKEDIN,  # Not configured in twitter_service
            keywords=["AI"],
            max_results=5,
        )

        result = await twitter_service.search_posts(query)

        # Should fail gracefully
        assert not result.success
        assert "not configured" in result.error_details.lower()

    @pytest.mark.asyncio()
    async def test_should_handle_api_rate_limiting(self, twitter_service):
        """
        Test: Should track and respect API rate limits
        with proper rate limit reporting.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.TWITTER,
            keywords=["AI"],
            max_results=5,
        )

        # Make multiple requests to test rate limiting
        results = []
        for _ in range(3):
            result = await twitter_service.search_posts(query)
            results.append(result)

        # All should succeed (with mocks)
        for result in results:
            assert result.success
            # Rate limit should be tracked
            assert hasattr(result, "rate_limit_remaining")
            assert result.rate_limit_remaining >= 0

    # ========================================================================
    # PERFORMANCE AND SCALABILITY TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_complete_search_within_reasonable_time(
        self,
        social_media_service,
    ):
        """
        Test: Should complete social media searches within acceptable time limits
        even with complex filtering and sentiment analysis.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.TWITTER,
            keywords=["AI", "machine learning"],
            hashtags=["AI", "Innovation"],
            min_engagement=10,
            max_results=20,
        )

        result = await social_media_service.search_posts(query)

        # Should complete quickly
        assert result.success
        assert result.execution_time < 3.0  # Should complete within 3 seconds

    @pytest.mark.asyncio()
    async def test_should_respect_max_results_limit(self, social_media_service):
        """
        Test: Should properly limit results according to max_results parameter
        and provide accurate count statistics.
        """
        query = SocialMediaQuery(
            platform=SocialPlatform.TWITTER,
            keywords=["AI"],
            max_results=2,  # Very small limit
        )

        result = await social_media_service.search_posts(query)

        # Should respect limit
        assert result.success
        assert len(result.posts) <= query.max_results
        assert result.processed_posts <= query.max_results

    # ========================================================================
    # HEALTH CHECK AND MAINTENANCE TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_provide_comprehensive_health_status(
        self,
        social_media_service,
    ):
        """
        Test: Should provide detailed health check information including
        platform status, rate limits, and service availability.
        """
        health_status = await social_media_service.health_check()

        # Verify health check structure
        assert "status" in health_status
        assert "platforms" in health_status
        assert "cache_size" in health_status
        assert "total_rate_limits" in health_status

        # Should be healthy with mock setup
        assert health_status["status"] == "healthy"

        # Should have all configured platforms
        assert "twitter" in health_status["platforms"]
        assert "linkedin" in health_status["platforms"]
        assert "reddit" in health_status["platforms"]

    @pytest.mark.asyncio()
    async def test_should_cleanup_resources_properly(self, social_media_service):
        """
        Test: Should properly close connections and clean up resources
        when service is shut down.
        """
        # Establish connections first
        query = SocialMediaQuery(
            platform=SocialPlatform.TWITTER,
            keywords=["AI"],
            max_results=1,
        )
        await social_media_service.search_posts(query)

        # Verify connections exist
        assert len(social_media_service._client_pool) > 0

        # Close service
        await social_media_service.close()

        # Verify cleanup
        assert len(social_media_service._client_pool) == 0
        assert len(social_media_service._post_cache) == 0
        assert len(social_media_service._rate_limits) == 0


class TestSocialMediaDataStructures:
    """Test social media-specific data structures and configurations"""

    def test_social_media_query_should_have_sensible_defaults(self):
        """
        Test: SocialMediaQuery should provide reasonable default values
        for all configuration parameters.
        """
        query = SocialMediaQuery(platform=SocialPlatform.TWITTER)

        # Verify defaults
        assert query.platform == SocialPlatform.TWITTER
        assert query.keywords == []
        assert query.hashtags == []
        assert query.accounts == []
        assert query.subreddits == []
        assert query.date_range is None
        assert query.max_results == 100
        assert query.min_engagement == 0
        assert query.exclude_retweets
        assert query.include_comments == False
        assert query.content_language == "en"
        assert query.sentiment_filter is None

    def test_social_media_post_should_be_immutable(self):
        """
        Test: SocialMediaPost instances should be immutable to ensure
        data integrity throughout processing pipeline.
        """
        post = SocialMediaPost(
            post_id="test_post_001",
            platform=SocialPlatform.TWITTER,
            author="@test_user",
            author_verified=True,
            content="Test content",
            timestamp=datetime.now(UTC),
            url="https://twitter.com/test",
            engagement_metrics={"likes": 100},
        )

        # Should be frozen dataclass (immutable)
        with pytest.raises(AttributeError):
            post.content = "Modified content"

    def test_social_platform_enum_should_have_correct_values(self):
        """
        Test: SocialPlatform enum should have correct platform identifiers
        for supported social media platforms.
        """
        assert SocialPlatform.TWITTER.value == "twitter"
        assert SocialPlatform.LINKEDIN.value == "linkedin"
        assert SocialPlatform.REDDIT.value == "reddit"

        # Should have exactly these platforms
        platforms = list(SocialPlatform)
        assert len(platforms) == 3
