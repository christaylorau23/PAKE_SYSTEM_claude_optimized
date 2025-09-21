#!/usr/bin/env python3
"""
PAKE System - Phase 2B RSS/Atom Feed Service Tests
TDD RED phase: Comprehensive failing tests for RSS/Atom feed ingestion service.

Following CLAUDE.md TDD principles for RSS feed implementation.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import Phase 2B services
from scripts.ingestion_pipeline import ContentItem

# Import RSS service (will be created)
try:
    from services.ingestion.rss_feed_service import (
        RSSError,
        RSSFeedItem,
        RSSFeedQuery,
        RSSFeedResult,
        RSSFeedService,
    )
except ImportError:
    # Expected during RED phase - RSS service doesn't exist yet
    RSSFeedService = None
    RSSFeedResult = None
    RSSFeedQuery = None
    RSSFeedItem = None
    RSSError = None


class TestRSSFeedService:
    """
    TDD test suite for Phase 2B RSS/Atom feed ingestion service.
    Tests comprehensive RSS feed parsing and content extraction capabilities.
    """

    @pytest.fixture
    def mock_cognitive_engine(self):
        """Mock cognitive engine for testing"""
        engine = Mock()
        engine.assess_content_quality = AsyncMock(return_value=0.87)
        engine.categorize_content = AsyncMock(return_value=["Technology", "AI"])
        engine.extract_insights = AsyncMock(
            return_value={
                "key_concepts": ["artificial intelligence", "machine learning"],
                "relevance_score": 0.91,
                "complexity_level": "intermediate",
            },
        )
        return engine

    @pytest.fixture
    def rss_feed_service(self):
        """Create RSS feed service instance"""
        if RSSFeedService is None:
            pytest.skip("RSSFeedService not implemented yet (RED phase)")

        return RSSFeedService()

    @pytest.fixture
    def sample_rss_xml(self):
        """Sample RSS 2.0 XML for testing"""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>AI Research Blog</title>
                <link>https://example.com/ai-blog</link>
                <description>Latest updates in AI research</description>
                <pubDate>Wed, 02 Jan 2025 12:00:00 GMT</pubDate>
                <item>
                    <title>Breakthrough in Neural Networks</title>
                    <link>https://example.com/ai-blog/neural-breakthrough</link>
                    <description>Scientists achieve new milestone in neural network efficiency</description>
                    <pubDate>Wed, 02 Jan 2025 10:30:00 GMT</pubDate>
                    <guid>https://example.com/ai-blog/neural-breakthrough</guid>
                    <category>Machine Learning</category>
                    <author>Dr. Jane Smith</author>
                </item>
                <item>
                    <title>Future of AI Ethics</title>
                    <link>https://example.com/ai-blog/ai-ethics</link>
                    <description>Exploring ethical considerations in AI development</description>
                    <pubDate>Tue, 01 Jan 2025 14:20:00 GMT</pubDate>
                    <guid>https://example.com/ai-blog/ai-ethics</guid>
                    <category>AI Ethics</category>
                    <author>Prof. John Doe</author>
                </item>
            </channel>
        </rss>"""

    @pytest.fixture
    def sample_atom_xml(self):
        """Sample Atom XML for testing"""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>Tech Innovation Feed</title>
            <link href="https://example.com/tech-feed" rel="self"/>
            <updated>2025-01-02T12:00:00Z</updated>
            <id>https://example.com/tech-feed</id>
            <entry>
                <title>Quantum Computing Advances</title>
                <link href="https://example.com/quantum-advances"/>
                <id>https://example.com/quantum-advances</id>
                <updated>2025-01-02T09:15:00Z</updated>
                <summary>Major breakthrough in quantum error correction</summary>
                <author>
                    <name>Dr. Alice Johnson</name>
                </author>
                <category term="Quantum Computing"/>
            </entry>
        </feed>"""

    # ========================================================================
    # CORE RSS FEED SERVICE TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_fetch_and_parse_rss_feed_successfully(
        self,
        rss_feed_service,
        sample_rss_xml,
    ):
        """
        Test: Should fetch RSS feed from URL and parse it into structured items
        """
        feed_url = "https://example.com/ai-blog/rss.xml"

        # Mock HTTP response
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value=sample_rss_xml)
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            # Test RSS feed parsing
            result = await rss_feed_service.fetch_feed(feed_url)

            # Verify result structure
            assert isinstance(result, RSSFeedResult)
            assert result.success
            assert result.feed_url == feed_url
            assert result.feed_title == "AI Research Blog"
            assert len(result.items) == 2

            # Verify first item
            first_item = result.items[0]
            assert isinstance(first_item, RSSFeedItem)
            assert first_item.title == "Breakthrough in Neural Networks"
            assert first_item.link == "https://example.com/ai-blog/neural-breakthrough"
            assert (
                first_item.description
                == "Scientists achieve new milestone in neural network efficiency"
            )
            assert first_item.author == "Dr. Jane Smith"
            assert "Machine Learning" in first_item.categories

    @pytest.mark.asyncio
    async def test_should_fetch_and_parse_atom_feed_successfully(
        self,
        rss_feed_service,
        sample_atom_xml,
    ):
        """
        Test: Should fetch Atom feed from URL and parse it into structured items
        """
        feed_url = "https://example.com/tech-feed/atom.xml"

        # Mock HTTP response
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value=sample_atom_xml)
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            # Test Atom feed parsing
            result = await rss_feed_service.fetch_feed(feed_url)

            # Verify result structure
            assert isinstance(result, RSSFeedResult)
            assert result.success
            assert result.feed_url == feed_url
            assert result.feed_title == "Tech Innovation Feed"
            assert len(result.items) == 1

            # Verify Atom item
            atom_item = result.items[0]
            assert isinstance(atom_item, RSSFeedItem)
            assert atom_item.title == "Quantum Computing Advances"
            assert atom_item.link == "https://example.com/quantum-advances"
            assert (
                atom_item.description
                == "Major breakthrough in quantum error correction"
            )
            assert atom_item.author == "Dr. Alice Johnson"
            assert "Quantum Computing" in atom_item.categories

    @pytest.mark.asyncio
    async def test_should_handle_multiple_feed_urls_concurrently(
        self,
        rss_feed_service,
    ):
        """
        Test: Should process multiple RSS/Atom feeds concurrently with proper error handling
        """
        feed_urls = [
            "https://example.com/tech-rss.xml",
            "https://example.com/science-atom.xml",
            "https://example.com/ai-news.xml",
        ]

        query = RSSFeedQuery(
            feed_urls=feed_urls,
            max_items_per_feed=5,
            fetch_full_content=False,
        )

        # Mock responses
        with patch.object(rss_feed_service, "fetch_feed") as mock_fetch:
            # Mock successful responses
            mock_fetch.side_effect = [
                RSSFeedResult(
                    success=True,
                    feed_url=url,
                    feed_title=f"Feed {i}",
                    items=[
                        RSSFeedItem(
                            title=f"Article {i}",
                            link=f"https://example.com/article-{i}",
                            description=f"Content {i}",
                            published=datetime.now(UTC),
                            guid=f"guid-{i}",
                            author=f"Author {i}",
                            categories=[f"Category {i}"],
                        ),
                    ],
                )
                for i, url in enumerate(feed_urls)
            ]

            # Execute concurrent fetching
            result = await rss_feed_service.fetch_multiple_feeds(query)

            # Verify concurrent execution
            assert isinstance(result, RSSFeedResult)
            assert result.success
            assert len(result.items) == 3  # One item from each feed
            assert result.feeds_processed == 3
            assert result.feeds_failed == 0

    @pytest.mark.asyncio
    async def test_should_filter_items_by_date_range(
        self,
        rss_feed_service,
        sample_rss_xml,
    ):
        """
        Test: Should filter RSS items based on publication date range
        """
        feed_url = "https://example.com/ai-blog/rss.xml"

        # Create query with date filtering
        query = RSSFeedQuery(
            feed_urls=[feed_url],
            date_from=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
            date_to=datetime(2025, 1, 2, 23, 59, 59, tzinfo=UTC),
            max_items_per_feed=10,
        )

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value=sample_rss_xml)
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_feed_service.fetch_with_query(query)

            # Should only return items from Jan 2, 2025
            assert result.success
            # Only "Breakthrough in Neural Networks" from Jan 2
            assert len(result.items) == 1
            assert result.items[0].title == "Breakthrough in Neural Networks"

    @pytest.mark.asyncio
    async def test_should_filter_items_by_keywords(
        self,
        rss_feed_service,
        sample_rss_xml,
    ):
        """
        Test: Should filter RSS items based on keyword matching in title/description
        """
        feed_url = "https://example.com/ai-blog/rss.xml"

        # Create query with keyword filtering
        query = RSSFeedQuery(
            feed_urls=[feed_url],
            keywords=["neural", "networks"],
            keyword_match_mode="any",  # Match any keyword
            max_items_per_feed=10,
        )

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value=sample_rss_xml)
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_feed_service.fetch_with_query(query)

            # Should only return items containing "neural" or "networks"
            assert result.success
            assert len(result.items) == 1
            assert (
                "neural" in result.items[0].title.lower()
                or "networks" in result.items[0].title.lower()
            )

    # ========================================================================
    # CONTENT EXTRACTION AND PROCESSING TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_fetch_full_article_content_when_requested(
        self,
        rss_feed_service,
    ):
        """
        Test: Should fetch full article content from item URLs when requested
        """
        feed_url = "https://example.com/blog/rss.xml"

        query = RSSFeedQuery(
            feed_urls=[feed_url],
            fetch_full_content=True,
            max_items_per_feed=5,
        )

        # Mock feed and article content
        with (
            patch.object(rss_feed_service, "fetch_feed") as mock_fetch_feed,
            patch.object(
                rss_feed_service,
                "fetch_article_content",
            ) as mock_fetch_article,
        ):
            # Mock RSS feed response
            mock_fetch_feed.return_value = RSSFeedResult(
                success=True,
                feed_url=feed_url,
                feed_title="Test Blog",
                items=[
                    RSSFeedItem(
                        title="Test Article",
                        link="https://example.com/article-1",
                        description="Short description",
                        published=datetime.now(UTC),
                        guid="article-1",
                        author="Test Author",
                        categories=["Tech"],
                    ),
                ],
            )

            # Mock article content
            mock_fetch_article.return_value = (
                "Full article content with detailed information..."
            )

            result = await rss_feed_service.fetch_with_query(query)

            # Verify full content was fetched
            assert result.success
            assert len(result.items) == 1
            assert result.items[0].full_content is not None
            assert "Full article content" in result.items[0].full_content
            assert mock_fetch_article.called

    @pytest.mark.asyncio
    async def test_should_convert_rss_items_to_content_items(self, rss_feed_service):
        """
        Test: Should convert RSS feed items to standardized ContentItem format
        """
        # Create RSS feed result
        rss_result = RSSFeedResult(
            success=True,
            feed_url="https://example.com/rss.xml",
            feed_title="Test Feed",
            items=[
                RSSFeedItem(
                    title="AI Advancement",
                    link="https://example.com/ai-advancement",
                    description="Latest AI research breakthrough",
                    published=datetime.now(UTC),
                    guid="ai-advancement-1",
                    author="Dr. Smith",
                    categories=["AI", "Research"],
                    full_content="Detailed content about AI advancement...",
                ),
            ],
        )

        # Convert to content items
        content_items = await rss_feed_service.to_content_items(
            rss_result,
            "rss_ingestion_test",
        )

        # Verify conversion
        assert len(content_items) == 1

        item = content_items[0]
        assert isinstance(item, ContentItem)
        assert item.source_name == "rss_ingestion_test"
        assert item.source_type == "rss"
        assert item.title == "AI Advancement"
        assert item.url == "https://example.com/ai-advancement"
        assert item.author == "Dr. Smith"
        assert "AI" in item.tags
        assert "Research" in item.tags
        assert "Detailed content about AI advancement" in item.content

    @pytest.mark.asyncio
    async def test_should_integrate_with_cognitive_assessment(
        self,
        rss_feed_service,
        mock_cognitive_engine,
    ):
        """
        Test: Should apply cognitive assessment to RSS feed content
        """
        feed_url = "https://example.com/tech-rss.xml"

        query = RSSFeedQuery(
            feed_urls=[feed_url],
            enable_cognitive_assessment=True,
            max_items_per_feed=3,
        )

        with patch.object(rss_feed_service, "fetch_feed") as mock_fetch:
            mock_fetch.return_value = RSSFeedResult(
                success=True,
                feed_url=feed_url,
                feed_title="Tech Blog",
                items=[
                    RSSFeedItem(
                        title="Machine Learning Trends",
                        link="https://example.com/ml-trends",
                        description="Overview of current ML trends",
                        published=datetime.now(UTC),
                        guid="ml-trends-1",
                        author="ML Expert",
                        categories=["ML", "Trends"],
                    ),
                ],
            )

            result = await rss_feed_service.fetch_with_cognitive_assessment(
                query,
                mock_cognitive_engine,
            )

            # Verify cognitive assessment was applied
            assert result.success
            assert result.cognitive_assessment_applied
            assert len(result.items) == 1

            # Check cognitive metadata
            item = result.items[0]
            assert hasattr(item, "cognitive_metadata")
            assert item.cognitive_metadata is not None
            assert "quality_score" in item.cognitive_metadata
            assert "categories" in item.cognitive_metadata
            assert "insights" in item.cognitive_metadata

    # ========================================================================
    # ERROR HANDLING AND RESILIENCE TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_handle_invalid_feed_urls_gracefully(self, rss_feed_service):
        """
        Test: Should handle invalid or unreachable RSS feed URLs gracefully
        """
        invalid_urls = [
            "https://nonexistent-domain-test.com/rss.xml",
            "not-a-valid-url",
            "https://httpstat.us/500/rss.xml",  # Returns 500 error
        ]

        for url in invalid_urls:
            result = await rss_feed_service.fetch_feed(url)

            # Should fail gracefully
            assert isinstance(result, RSSFeedResult)
            assert not result.success
            assert isinstance(result.error, RSSError)
            assert result.error.is_retryable or result.error.error_code in [
                "INVALID_URL",
                "NOT_FOUND",
            ]

    @pytest.mark.asyncio
    async def test_should_handle_malformed_xml_gracefully(self, rss_feed_service):
        """
        Test: Should handle malformed RSS/Atom XML gracefully
        """
        malformed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Broken Feed</title>
                <!-- Missing closing tags and malformed structure -->
                <item>
                    <title>Incomplete Item
                    <link>https://example.com/broken-link
        </rss>"""

        feed_url = "https://example.com/broken-feed.xml"

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value=malformed_xml)
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await rss_feed_service.fetch_feed(feed_url)

            # Should handle parsing errors gracefully
            assert isinstance(result, RSSFeedResult)
            assert not result.success
            assert isinstance(result.error, RSSError)
            assert result.error.error_code == "PARSE_ERROR"

    @pytest.mark.asyncio
    async def test_should_implement_retry_logic_for_temporary_failures(
        self,
        rss_feed_service,
    ):
        """
        Test: Should retry failed requests with exponential backoff
        """
        feed_url = "https://example.com/unreliable-feed.xml"
        call_count = 0

        class MockFailingResponse:
            def __init__(self, call_count):
                self.call_count = call_count

            async def __aenter__(self):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:  # Fail first 2 attempts
                    raise Exception("Network timeout")
                # Succeed on 3rd attempt
                mock_response = AsyncMock()
                mock_response.text = AsyncMock(
                    return_value="<rss><channel><title>Success</title></channel></rss>",
                )
                mock_response.status = 200
                return mock_response

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        def mock_failing_request(*args, **kwargs):
            return MockFailingResponse(call_count)

        with patch("aiohttp.ClientSession.get", side_effect=mock_failing_request):
            result = await rss_feed_service.fetch_feed(feed_url, max_retries=3)

            # Should succeed after retries
            assert call_count == 3  # 2 failures + 1 success
            assert result.success

    @pytest.mark.asyncio
    async def test_should_respect_feed_rate_limiting(self, rss_feed_service):
        """
        Test: Should respect rate limiting and backoff requirements
        """
        feed_urls = [f"https://example.com/feed-{i}.xml" for i in range(5)]

        start_time = asyncio.get_event_loop().time()

        # Mock rate-limited responses
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(
                return_value="<rss><channel><title>Rate Limited</title></channel></rss>",
            )
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            # Process multiple feeds with rate limiting
            results = []
            for url in feed_urls:
                # 100ms delay
                result = await rss_feed_service.fetch_feed(url, rate_limit_delay=0.1)
                results.append(result)

        end_time = asyncio.get_event_loop().time()
        execution_time = end_time - start_time

        # Should take at least 0.4 seconds (4 delays of 100ms between 5 requests)
        assert execution_time >= 0.4
        assert all(result.success for result in results)

    # ========================================================================
    # PERFORMANCE AND CACHING TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_implement_intelligent_caching(self, rss_feed_service):
        """
        Test: Should cache RSS feed results to improve performance
        """
        feed_url = "https://example.com/cached-feed.xml"

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(
                return_value="<rss><channel><title>Cached Feed</title></channel></rss>",
            )
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            # First request - should make HTTP call
            result1 = await rss_feed_service.fetch_feed(feed_url, enable_caching=True)
            assert result1.success
            assert mock_get.call_count == 1

            # Second request - should use cache
            result2 = await rss_feed_service.fetch_feed(feed_url, enable_caching=True)
            assert result2.success
            assert result2.from_cache
            assert mock_get.call_count == 1  # No additional HTTP calls

    @pytest.mark.asyncio
    async def test_should_handle_concurrent_requests_efficiently(
        self,
        rss_feed_service,
    ):
        """
        Test: Should handle multiple concurrent RSS feed requests efficiently
        """
        feed_urls = [f"https://example.com/concurrent-feed-{i}.xml" for i in range(10)]

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(
                return_value="<rss><channel><title>Concurrent</title></channel></rss>",
            )
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            # Execute concurrent requests
            start_time = asyncio.get_event_loop().time()
            tasks = [rss_feed_service.fetch_feed(url) for url in feed_urls]
            results = await asyncio.gather(*tasks)
            end_time = asyncio.get_event_loop().time()

            # Should complete much faster than sequential execution
            execution_time = end_time - start_time
            assert execution_time < 2.0  # Should complete in under 2 seconds
            assert len(results) == 10
            assert all(result.success for result in results)

    # ========================================================================
    # INTEGRATION AND WORKFLOW TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_integrate_with_orchestrator_workflow(self, rss_feed_service):
        """
        Test: Should integrate seamlessly with the ingestion orchestrator
        """
        # This test ensures RSS service follows the same patterns as other services
        query = RSSFeedQuery(
            feed_urls=["https://example.com/orchestrator-test.xml"],
            max_items_per_feed=5,
        )

        with patch.object(rss_feed_service, "fetch_multiple_feeds") as mock_fetch:
            mock_fetch.return_value = RSSFeedResult(
                success=True,
                feed_url="test",
                feed_title="Test",
                items=[
                    RSSFeedItem(
                        title="Orchestrator Test",
                        link="https://example.com/test",
                        description="Test item",
                        published=datetime.now(UTC),
                        guid="test-1",
                        author="Tester",
                        categories=["Test"],
                    ),
                ],
            )

            # Test orchestrator-compatible execution
            result = await rss_feed_service.execute_ingestion_query(
                query,
                "rss_orchestrator_test",
            )

            # Should return ContentItem list compatible with orchestrator
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], ContentItem)
            assert result[0].source_type == "rss"


if __name__ == "__main__":
    # Run RSS feed service tests
    pytest.main([__file__, "-v", "--tb=short"])
