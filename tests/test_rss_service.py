#!/usr/bin/env python3
"""
PAKE System - RSS/Atom Feed Service Tests
Phase 2B Sprint 3: Comprehensive TDD testing for RSS/Atom feed ingestion

Tests RSS/Atom feed parsing, real-time monitoring, intelligent filtering,
and cognitive quality assessment.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from services.ingestion.rss_service import (
    FeedConfiguration,
    FeedItem,
    RSSFeedService,
)

from scripts.ingestion_pipeline import ContentItem


class TestRSSFeedService:
    """
    Comprehensive test suite for RSS/Atom feed ingestion service.
    Tests feed parsing, content filtering, and cognitive integration.
    """

    @pytest.fixture()
    def rss_config(self):
        """Standard RSS feed configuration"""
        return FeedConfiguration(
            url="https://example.com/rss.xml",
            name="Example Tech Blog",
            category="technology",
            update_interval=3600,
            max_items_per_fetch=20,
            min_content_length=150,
        )

    @pytest.fixture()
    def atom_config(self):
        """Atom feed configuration"""
        return FeedConfiguration(
            url="https://example.com/atom.xml",
            name="Example News Feed",
            category="news",
            update_interval=1800,
            max_items_per_fetch=30,
            keyword_filters=["AI", "technology"],
            exclude_keywords=["spam", "advertisement"],
        )

    @pytest.fixture()
    def mock_cognitive_engine(self):
        """Mock cognitive engine for quality assessment"""
        engine = Mock()
        engine.assess_content_quality = AsyncMock(return_value=0.82)
        return engine

    @pytest.fixture()
    def rss_service(self, mock_cognitive_engine):
        """Create RSS service instance"""
        return RSSFeedService(cognitive_engine=mock_cognitive_engine)

    @pytest.fixture()
    def sample_rss_content(self):
        """Sample RSS 2.0 XML content"""
        return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Tech Blog RSS Feed</title>
        <description>Latest technology news and insights</description>
        <link>https://example.com</link>
        <lastBuildDate>Wed, 06 Sep 2025 10:00:00 GMT</lastBuildDate>

        <item>
            <title>Revolutionary AI Breakthrough in Natural Language Processing</title>
            <link>https://example.com/ai-breakthrough</link>
            <description>Scientists have achieved a major breakthrough in natural language processing, developing AI systems that can understand context and nuance with unprecedented accuracy. This advancement promises to transform human-computer interaction across industries.</description>
            <pubDate>Wed, 06 Sep 2025 09:00:00 GMT</pubDate>
            <guid>https://example.com/ai-breakthrough</guid>
            <category>Artificial Intelligence</category>
            <author>Dr. Sarah Johnson</author>
        </item>

        <item>
            <title>Quantum Computing Reaches New Milestone</title>
            <link>https://example.com/quantum-milestone</link>
            <description>Researchers announce significant progress in quantum computing stability, bringing practical quantum applications closer to reality. The new quantum processors demonstrate error rates low enough for commercial viability.</description>
            <pubDate>Wed, 06 Sep 2025 08:00:00 GMT</pubDate>
            <guid>https://example.com/quantum-milestone</guid>
            <category>Quantum Computing</category>
            <author>Prof. Michael Chen</author>
        </item>
    </channel>
</rss>"""

    @pytest.fixture()
    def sample_atom_content(self):
        """Sample Atom 1.0 XML content"""
        return """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>News Feed</title>
    <subtitle>Breaking technology news</subtitle>
    <link href="https://example.com/"/>
    <updated>2025-09-06T10:00:00Z</updated>
    <id>https://example.com/feed</id>

    <entry>
        <title>Machine Learning Transforms Healthcare Diagnostics</title>
        <link href="https://example.com/ml-healthcare"/>
        <id>https://example.com/ml-healthcare</id>
        <updated>2025-09-06T09:30:00Z</updated>
        <published>2025-09-06T09:30:00Z</published>
        <summary>Machine learning algorithms are revolutionizing medical diagnostics by analyzing medical imaging with greater accuracy than traditional methods. Early trials show 95% accuracy in cancer detection.</summary>
        <content type="html">Machine learning algorithms are revolutionizing medical diagnostics by analyzing medical imaging with greater accuracy than traditional methods. Early trials show 95% accuracy in cancer detection, promising earlier intervention and better patient outcomes.</content>
        <author>
            <name>Dr. Emily Rodriguez</name>
        </author>
        <category term="Healthcare"/>
        <category term="Machine Learning"/>
    </entry>
</feed>"""

    # ========================================================================
    # RSS FEED PARSING TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_fetch_and_parse_rss_feed_successfully(
        self,
        rss_service,
        rss_config,
        sample_rss_content,
    ):
        """
        Test: Should fetch and parse RSS 2.0 feeds with proper
        item extraction and metadata preservation.
        """
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=sample_rss_content)
        mock_response.headers = {"Content-Type": "application/rss+xml"}

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_service.fetch_feed(rss_config)

        # Verify feed parsing success
        assert result.success
        assert result.feed_config == rss_config
        assert len(result.items) > 0
        assert result.total_items_found >= len(result.items)
        assert result.http_status == 200
        assert result.execution_time > 0

        # Verify RSS-specific parsing
        item = result.items[0]
        assert isinstance(item, FeedItem)
        assert (
            item.title == "Revolutionary AI Breakthrough in Natural Language Processing"
        )
        assert item.url == "https://example.com/ai-breakthrough"
        assert item.author == "Dr. Sarah Johnson"
        assert "Artificial Intelligence" in item.categories
        assert item.feed_name == rss_config.name

    @pytest.mark.asyncio()
    async def test_should_parse_atom_feeds_correctly(
        self,
        rss_service,
        atom_config,
        sample_atom_content,
    ):
        """
        Test: Should parse Atom 1.0 feeds with proper namespace handling
        and content extraction.
        """
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=sample_atom_content)
        mock_response.headers = {"Content-Type": "application/atom+xml"}

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_service.fetch_feed(atom_config)

        # Verify Atom parsing success
        assert result.success
        assert len(result.items) > 0

        # Verify Atom-specific parsing
        item = result.items[0]
        assert item.title == "Machine Learning Transforms Healthcare Diagnostics"
        assert item.url == "https://example.com/ml-healthcare"
        assert item.author == "Dr. Emily Rodriguez"
        assert "Healthcare" in item.categories
        assert "Machine Learning" in item.categories
        assert (
            item.content
        )  # Should have content from both summary and content elements

    @pytest.mark.asyncio()
    async def test_should_handle_malformed_xml_gracefully(
        self,
        rss_service,
        rss_config,
    ):
        """
        Test: Should handle malformed XML feeds with proper error reporting
        and recovery strategies.
        """
        malformed_xml = """<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Broken Feed</title>
        <item>
            <title>Unclosed tag example
            <link>https://example.com/broken</link>
        </item>
    </channel>
</rss>"""

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=malformed_xml)

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_service.fetch_feed(rss_config)

        # Should fail gracefully
        assert not result.success
        assert "parsing failed" in result.error_details.lower()
        assert result.execution_time > 0

    # ========================================================================
    # CONTENT FILTERING TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_apply_keyword_filtering_accurately(
        self,
        rss_service,
        sample_rss_content,
    ):
        """
        Test: Should filter RSS items by keywords with case-insensitive matching
        and support for multiple keyword patterns.
        """
        config = FeedConfiguration(
            url="https://example.com/rss.xml",
            name="Filtered Feed",
            keyword_filters=["AI", "artificial intelligence", "quantum"],
            max_items_per_fetch=10,
        )

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=sample_rss_content)

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_service.fetch_feed(config)

        # Verify keyword filtering
        assert result.success

        for item in result.items:
            content_text = f"{item.title} {item.content}".lower()
            # Should contain at least one of the keywords
            keywords_lower = [kw.lower() for kw in config.keyword_filters]
            assert any(keyword in content_text for keyword in keywords_lower)

    @pytest.mark.asyncio()
    async def test_should_exclude_content_by_exclude_keywords(
        self,
        rss_service,
        sample_rss_content,
    ):
        """
        Test: Should exclude RSS items containing specified exclude keywords
        to filter out unwanted content.
        """
        config = FeedConfiguration(
            url="https://example.com/rss.xml",
            name="Filtered Feed",
            exclude_keywords=["spam", "advertisement", "promotion"],
            max_items_per_fetch=10,
        )

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=sample_rss_content)

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_service.fetch_feed(config)

        # Verify exclusion filtering
        assert result.success

        for item in result.items:
            content_text = f"{item.title} {item.content}".lower()
            exclude_keywords_lower = [kw.lower() for kw in config.exclude_keywords]
            # Should not contain any exclude keywords
            assert not any(
                keyword in content_text for keyword in exclude_keywords_lower
            )

    @pytest.mark.asyncio()
    async def test_should_apply_minimum_content_length_filter(self, rss_service):
        """
        Test: Should filter out RSS items with insufficient content length
        to focus on substantial articles.
        """
        short_content_rss = """<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Test Feed</title>
        <item>
            <title>Short Article</title>
            <link>https://example.com/short</link>
            <description>Too short.</description>
        </item>
        <item>
            <title>Long Article with Substantial Content</title>
            <link>https://example.com/long</link>
            <description>This is a much longer article with substantial content that provides detailed information about the topic. It contains enough content to meet the minimum length requirements and should pass the filtering criteria.</description>
        </item>
    </channel>
</rss>"""

        config = FeedConfiguration(
            url="https://example.com/rss.xml",
            name="Length Filtered Feed",
            min_content_length=100,  # Require substantial content
            max_items_per_fetch=10,
        )

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=short_content_rss)

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_service.fetch_feed(config)

        # Should only have the long article
        assert result.success
        assert len(result.items) == 1
        assert "Long Article" in result.items[0].title
        assert len(result.items[0].content) >= config.min_content_length

    # ========================================================================
    # DEDUPLICATION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_deduplicate_items_by_url_and_title(
        self,
        rss_service,
        rss_config,
    ):
        """
        Test: Should remove duplicate items based on URL and title similarity
        to avoid processing the same content multiple times.
        """
        duplicate_rss = """<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Test Feed</title>
        <item>
            <title>Unique Article One</title>
            <link>https://example.com/article1</link>
            <description>First unique article with original content.</description>
            <guid>guid1</guid>
        </item>
        <item>
            <title>Unique Article One</title>
            <link>https://example.com/article1</link>
            <description>Duplicate of the first article.</description>
            <guid>guid2</guid>
        </item>
        <item>
            <title>Unique Article Two</title>
            <link>https://example.com/article2</link>
            <description>Second unique article with different content.</description>
            <guid>guid3</guid>
        </item>
    </channel>
</rss>"""

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=duplicate_rss)

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_service.fetch_feed(rss_config)

        # Should only have unique items
        assert result.success
        assert len(result.items) == 2  # Only unique articles

        # Verify unique titles and URLs
        titles = [item.title for item in result.items]
        urls = [item.url for item in result.items]

        assert len(set(titles)) == 2  # All unique titles
        assert len(set(urls)) == 2  # All unique URLs

    # ========================================================================
    # COGNITIVE INTEGRATION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_integrate_cognitive_quality_assessment(
        self,
        rss_service,
        rss_config,
        sample_rss_content,
    ):
        """
        Test: Should apply cognitive quality assessment to RSS feed items
        and incorporate quality scores into item metadata.
        """
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=sample_rss_content)

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_service.fetch_feed(rss_config)

        # Verify cognitive integration
        assert result.success
        assert result.cognitive_assessments_applied > 0

        # Verify quality scores are applied
        for item in result.items:
            assert hasattr(item, "quality_score")
            assert 0.0 <= item.quality_score <= 1.0

        # Verify cognitive engine was called
        assert rss_service.cognitive_engine.assess_content_quality.call_count > 0

    # ========================================================================
    # HTTP CACHING TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_handle_http_304_not_modified_efficiently(
        self,
        rss_service,
        rss_config,
    ):
        """
        Test: Should handle HTTP 304 Not Modified responses efficiently
        using ETags and Last-Modified headers for bandwidth optimization.
        """
        # First request - should get content
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value="<rss><channel><item><title>Test</title></item></channel></rss>",
        )
        mock_response.headers = {
            "ETag": "test-etag",
            "Last-Modified": "Wed, 06 Sep 2025 10:00:00 GMT",
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            # First fetch
            result1 = await rss_service.fetch_feed(rss_config)
            assert result1.success

            # Second request - should return 304
            mock_response.status = 304
            result2 = await rss_service.fetch_feed(rss_config)

            assert result2.success
            assert result2.http_status == 304
            # Should be faster due to no content processing
            assert result2.execution_time <= result1.execution_time

    # ========================================================================
    # CONTENT ITEM CONVERSION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_convert_feed_items_to_content_items_correctly(
        self,
        rss_service,
        rss_config,
        sample_rss_content,
    ):
        """
        Test: Should convert RSS feed items to standardized ContentItem format
        with comprehensive metadata preservation.
        """
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=sample_rss_content)

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_service.fetch_feed(rss_config)
            content_items = await rss_service.to_content_items(
                result,
                "rss_ingestion_test",
            )

        # Verify conversion success
        assert len(content_items) == len(result.items)

        for i, item in enumerate(content_items):
            feed_item = result.items[i]

            # Verify ContentItem structure
            assert isinstance(item, ContentItem)
            assert item.source_name == "rss_ingestion_test"
            assert item.source_type == "rss_feed"
            assert item.title == feed_item.title
            assert item.content == feed_item.content
            assert item.author == feed_item.author
            assert item.published == feed_item.published
            assert item.url == feed_item.url

            # Verify metadata preservation
            assert item.metadata["item_id"] == feed_item.item_id
            assert item.metadata["feed_url"] == feed_item.feed_url
            assert item.metadata["feed_name"] == feed_item.feed_name
            assert item.metadata["categories"] == feed_item.categories
            assert item.metadata["quality_score"] == feed_item.quality_score
            assert item.metadata["word_count"] == feed_item.word_count

    # ========================================================================
    # ERROR HANDLING TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_handle_http_errors_gracefully(self, rss_service, rss_config):
        """
        Test: Should handle HTTP errors (404, 500, etc.) with proper
        error reporting and recovery strategies.
        """
        mock_response = Mock()
        mock_response.status = 404
        mock_response.reason = "Not Found"

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_service.fetch_feed(rss_config)

        # Should fail gracefully
        assert not result.success
        assert "404" in result.error_details
        assert result.http_status == 404
        assert result.execution_time > 0

    @pytest.mark.asyncio()
    async def test_should_handle_network_timeouts_appropriately(
        self,
        rss_service,
        rss_config,
    ):
        """
        Test: Should handle network timeouts with proper error reporting
        and timeout configuration.
        """
        with patch(
            "aiohttp.ClientSession.get",
            side_effect=TimeoutError("Request timeout"),
        ):
            result = await rss_service.fetch_feed(rss_config)

        # Should fail gracefully
        assert not result.success
        assert "timeout" in result.error_details.lower()
        assert result.execution_time > 0

    # ========================================================================
    # HEALTH CHECK AND MAINTENANCE TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_provide_comprehensive_health_status(self, rss_service):
        """
        Test: Should provide detailed health check information including
        cache statistics and service availability.
        """
        health_status = await rss_service.health_check()

        # Verify health check structure
        assert "status" in health_status
        assert "feed_cache_size" in health_status
        assert "item_cache_size" in health_status
        assert "http_session_active" in health_status
        assert "monitoring_tasks" in health_status

        # Should be healthy initially
        assert health_status["status"] == "healthy"
        assert health_status["feed_cache_size"] >= 0
        assert health_status["item_cache_size"] >= 0

    @pytest.mark.asyncio()
    async def test_should_cleanup_resources_properly(
        self,
        rss_service,
        rss_config,
        sample_rss_content,
    ):
        """
        Test: Should properly close connections and clean up resources
        when service is shut down.
        """
        # Use service to establish connections and cache
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=sample_rss_content)

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            await rss_service.fetch_feed(rss_config)

        # Verify some resources exist
        health_before = await rss_service.health_check()
        assert (
            health_before["feed_cache_size"] > 0 or health_before["item_cache_size"] > 0
        )

        # Close service
        await rss_service.close()

        # Verify cleanup
        health_after = await rss_service.health_check()
        assert health_after["feed_cache_size"] == 0
        assert health_after["item_cache_size"] == 0


class TestFeedDataStructures:
    """Test RSS/Atom feed-specific data structures"""

    def test_feed_configuration_should_have_sensible_defaults(self):
        """
        Test: FeedConfiguration should provide reasonable default values
        for all configuration parameters.
        """
        config = FeedConfiguration(url="https://example.com/feed.rss", name="Test Feed")

        # Verify defaults
        assert config.url == "https://example.com/feed.rss"
        assert config.name == "Test Feed"
        assert config.category == "general"
        assert config.update_interval == 3600
        assert config.max_items_per_fetch == 50
        assert config.content_filters == []
        assert config.keyword_filters == []
        assert config.exclude_keywords == []
        assert config.min_content_length == 100
        assert config.enable_full_content_extraction
        assert config.custom_headers == {}

    def test_feed_item_should_be_immutable(self):
        """
        Test: FeedItem instances should be immutable to ensure
        data integrity throughout processing pipeline.
        """
        item = FeedItem(
            item_id="test_item_001",
            feed_url="https://example.com/feed.rss",
            feed_name="Test Feed",
            title="Test Article",
            content="Test content",
            summary="Test summary",
            url="https://example.com/article",
            author="Test Author",
            published=datetime.now(UTC),
            updated=datetime.now(UTC),
        )

        # Should be frozen dataclass (immutable)
        with pytest.raises(AttributeError):
            item.title = "Modified title"
