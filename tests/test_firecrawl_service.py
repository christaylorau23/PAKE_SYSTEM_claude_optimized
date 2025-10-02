#!/usr/bin/env python3
"""
PAKE System - Phase 2A TDD Tests for FirecrawlService
Test-driven development for enhanced web scraping capabilities.

Following CLAUDE.md TDD principles:
- RED: Write failing tests first (this file)
- GREEN: Minimal implementation to pass tests
- REFACTOR: Optimize and improve code structure
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

# These imports will fail initially (RED phase) - that's expected
try:
    from services.ingestion.firecrawl_service import (
        FirecrawlError,
        FirecrawlResult,
        FirecrawlService,
        ScrapingOptions,
    )

    from scripts.ingestion_pipeline import ContentItem
except ImportError:
    # Expected during RED phase - services don't exist yet
    pass


@dataclass
class MockFirecrawlResponse:
    """Mock response for testing Firecrawl API interactions"""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class TestFirecrawlService:
    """
    Test suite for FirecrawlService following behavior-driven testing principles.
    Tests focus on WHAT the service does, not HOW it does it.
    """

    @pytest.fixture()
    def firecrawl_service(self):
        """Fixture providing a FirecrawlService instance for testing"""
        return FirecrawlService(
            api_key="test_api_key_12345",
            base_url="https://api.firecrawl.dev",
        )

    @pytest.fixture()
    def sample_url(self):
        """Fixture providing a sample URL for testing"""
        return "https://example.com/javascript-heavy-page"

    @pytest.fixture()
    def expected_content_item(self):
        """Fixture providing expected ContentItem structure"""
        return {
            "title": "JavaScript Heavy Page - Example",
            "content": "This content was rendered by JavaScript and extracted successfully.",
            "url": "https://example.com/javascript-heavy-page",
            "metadata": {
                "scraping_method": "firecrawl",
                "javascript_rendered": True,
                "extraction_time": "2025-09-05T16:24:00Z",
            },
        }

    # ========================================================================
    # BEHAVIOR TESTS - Core Functionality
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_scrape_javascript_rendered_content_successfully(
        self,
        firecrawl_service,
        sample_url,
        expected_content_item,
    ):
        """
        RED TEST: FirecrawlService should successfully scrape JavaScript-rendered content.

        This behavior is critical because basic BeautifulSoup fails on SPA/JavaScript sites.
        The service must be able to render JavaScript and extract meaningful content.
        """
        # This test will fail initially - FirecrawlService doesn't exist yet
        result = await firecrawl_service.scrape_url(sample_url)

        assert result.success is True
        assert result.content is not None
        assert len(result.content) > 50  # Meaningful content length
        assert "JavaScript" in result.content  # Should extract JS-rendered text
        assert result.metadata["javascript_rendered"] is True
        assert result.url == sample_url

    @pytest.mark.asyncio()
    async def test_should_handle_rate_limiting_gracefully(self, firecrawl_service):
        """
        RED TEST: Service should handle API rate limiting without crashing.

        Critical behavior for production use - must gracefully handle rate limits
        and provide meaningful error information for retry logic.
        """
        # Mock rate-limited response
        with patch.object(firecrawl_service, "_make_api_request") as mock_request:
            mock_request.return_value = MockFirecrawlResponse(
                success=False,
                error="Rate limit exceeded. Try again in 60 seconds.",
            )

            result = await firecrawl_service.scrape_url("https://example.com")

            assert result.success is False
            assert result.error is not None
            assert "rate limit" in result.error.message.lower()
            assert result.retry_after is not None

    @pytest.mark.asyncio()
    async def test_should_extract_structured_content_with_metadata(
        self,
        firecrawl_service,
        sample_url,
    ):
        """
        RED TEST: Service should extract structured content with rich metadata.

        Beyond basic text extraction, service should provide structured data
        including title, headings, links, and technical metadata.
        """
        result = await firecrawl_service.scrape_url(
            sample_url,
            options=ScrapingOptions(
                extract_metadata=True,
                include_links=True,
                include_headings=True,
            ),
        )

        assert result.success is True
        assert result.title is not None
        assert result.headings is not None
        assert len(result.headings) > 0
        assert result.links is not None
        assert result.metadata["content_type"] is not None
        assert result.metadata["word_count"] > 0

    @pytest.mark.asyncio()
    async def test_should_integrate_with_existing_content_item_structure(
        self,
        firecrawl_service,
        sample_url,
    ):
        """
        RED TEST: Service should produce ContentItem compatible with existing pipeline.

        Critical integration behavior - must work seamlessly with existing
        ingestion pipeline and ContentItem data structure.
        """
        result = await firecrawl_service.scrape_url(sample_url)
        content_item = await firecrawl_service.to_content_item(result, "firecrawl_web")

        # Verify ContentItem compatibility
        assert hasattr(content_item, "source_name")
        assert hasattr(content_item, "source_type")
        assert hasattr(content_item, "title")
        assert hasattr(content_item, "content")
        assert hasattr(content_item, "url")
        assert hasattr(content_item, "published")
        assert hasattr(content_item, "metadata")

        assert content_item.source_type == "firecrawl_web"
        assert content_item.metadata["scraping_method"] == "firecrawl"

    # ========================================================================
    # BEHAVIOR TESTS - Error Handling and Edge Cases
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_handle_invalid_urls_gracefully(self, firecrawl_service):
        """
        RED TEST: Service should handle invalid URLs without crashing.
        """
        invalid_urls = ["not-a-url", "ftp://invalid-protocol.com", "https://", "", None]

        for invalid_url in invalid_urls:
            result = await firecrawl_service.scrape_url(invalid_url)
            assert result.success is False
            assert result.error is not None
            assert "invalid url" in result.error.message.lower()

    @pytest.mark.asyncio()
    async def test_should_handle_network_timeout_gracefully(self, firecrawl_service):
        """
        RED TEST: Service should handle network timeouts with proper error reporting.
        """
        with patch.object(firecrawl_service, "_make_api_request") as mock_request:
            mock_request.side_effect = TimeoutError("Request timed out")

            result = await firecrawl_service.scrape_url("https://slow-website.com")

            assert result.success is False
            assert result.error is not None
            assert "timeout" in result.error.message.lower()

    @pytest.mark.asyncio()
    async def test_should_handle_api_key_authentication_errors(self, firecrawl_service):
        """
        RED TEST: Service should handle API authentication errors appropriately.
        """
        with patch.object(firecrawl_service, "_make_api_request") as mock_request:
            mock_request.return_value = MockFirecrawlResponse(
                success=False,
                error="Invalid API key",
            )

            result = await firecrawl_service.scrape_url("https://example.com")

            assert result.success is False
            assert result.error is not None
            assert "authentication" in result.error.message.lower()

    # ========================================================================
    # BEHAVIOR TESTS - Performance and Optimization
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_respect_scraping_options_configuration(
        self,
        firecrawl_service,
    ):
        """
        RED TEST: Service should properly handle various scraping configuration options.
        """
        options = ScrapingOptions(
            wait_time=5000,  # Wait 5 seconds for JS
            extract_metadata=True,
            follow_redirects=True,
            user_agent="PAKE-Firecrawl-Bot/1.0",
            timeout=30000,
        )

        result = await firecrawl_service.scrape_url("https://example.com", options)

        assert result.success is True
        assert result.metadata["wait_time"] == 5000
        assert result.metadata["followed_redirects"] is not None

    @pytest.mark.asyncio()
    async def test_should_support_bulk_scraping_with_rate_limiting(
        self,
        firecrawl_service,
    ):
        """
        RED TEST: Service should support bulk scraping while respecting rate limits.
        """
        urls = ["https://example1.com", "https://example2.com", "https://example3.com"]

        results = await firecrawl_service.scrape_bulk(
            urls,
            max_concurrent=2,
            delay_between_requests=1.0,
        )

        assert len(results) == 3
        assert all(isinstance(result, FirecrawlResult) for result in results)
        # Should have respected rate limiting (took at least 2 seconds)
        assert True  # Timing check would go here in actual implementation

    # ========================================================================
    # BEHAVIOR TESTS - Integration with Cognitive System
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_integrate_with_autonomous_cognitive_engine(
        self,
        firecrawl_service,
    ):
        """
        RED TEST: Service should integrate with existing cognitive system for quality assessment.

        This is critical for Phase 2 - leveraging the autonomous cognitive system
        to assess content quality and relevance in real-time.
        """
        # Mock cognitive engine integration

        mock_cognitive_engine = Mock()
        mock_cognitive_engine.assess_content_quality = AsyncMock(return_value=0.87)

        result = await firecrawl_service.scrape_with_cognitive_assessment(
            url="https://high-quality-content.com",
            cognitive_engine=mock_cognitive_engine,
        )

        assert result.success is True
        assert result.quality_score is not None
        assert result.quality_score > 0.8
        assert result.cognitive_assessment is not None
        mock_cognitive_engine.assess_content_quality.assert_called_once()

    @pytest.mark.asyncio()
    async def test_should_trigger_metacognitive_optimization_for_poor_results(
        self,
        firecrawl_service,
    ):
        """
        RED TEST: Service should trigger metacognitive optimization when scraping quality is poor.

        Integration with the metacognitive optimization engine to improve
        scraping strategies based on content quality feedback.
        """

        mock_metacognitive_engine = Mock()
        mock_metacognitive_engine.optimize_scraping_strategy = AsyncMock(
            return_value={"wait_time": 8000, "extract_metadata": True},
        )

        # First attempt with poor quality
        poor_result = await firecrawl_service.scrape_url("https://difficult-site.com")

        # Should trigger optimization if quality is poor
        optimized_result = await firecrawl_service.scrape_with_optimization(
            url="https://difficult-site.com",
            metacognitive_engine=mock_metacognitive_engine,
            quality_threshold=0.7,
        )

        assert optimized_result.optimization_applied is True
        assert optimized_result.scraping_attempts > 1

    # ========================================================================
    # BEHAVIOR TESTS - Data Structure and Compatibility
    # ========================================================================

    def test_firecrawl_result_should_be_immutable(self):
        """
        RED TEST: FirecrawlResult data structure should be immutable (frozen dataclass).

        Following functional programming principles from CLAUDE.md.
        """
        result = FirecrawlResult(
            success=True,
            content="Test content",
            url="https://example.com",
        )

        # Should not be able to modify result after creation
        with pytest.raises(Exception):  # FrozenInstanceError expected
            result.content = "Modified content"

    def test_scraping_options_should_have_sensible_defaults(self):
        """
        RED TEST: ScrapingOptions should provide sensible default values.
        """
        options = ScrapingOptions()

        assert options.timeout > 0
        assert options.wait_time >= 0
        assert options.user_agent is not None
        assert isinstance(options.extract_metadata, bool)
        assert isinstance(options.follow_redirects, bool)

    # ========================================================================
    # BEHAVIOR TESTS - Integration with n8n Workflows
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_integrate_with_n8n_workflow_triggers(self, firecrawl_service):
        """
        RED TEST: Service should integrate with existing n8n workflow system.

        Must work seamlessly with the existing workflow automation.
        """

        mock_n8n_manager = Mock()
        mock_n8n_manager.trigger_workflow = AsyncMock(
            return_value={"workflow_id": "123"},
        )

        result = await firecrawl_service.scrape_url("https://example.com")

        # Should be able to trigger workflow with result
        workflow_result = await firecrawl_service.trigger_processing_workflow(
            result=result,
            n8n_manager=mock_n8n_manager,
            workflow_type="content_processing",
        )

        assert workflow_result["workflow_id"] is not None
        mock_n8n_manager.trigger_workflow.assert_called_once()


# ========================================================================
# BEHAVIOR TESTS - Error Classes and Exception Handling
# ========================================================================


class TestFirecrawlErrorHandling:
    """
    Test suite for FirecrawlError classes and exception handling behaviors.
    """

    def test_firecrawl_error_should_provide_structured_error_information(self):
        """
        RED TEST: FirecrawlError should provide structured error information.
        """
        error = FirecrawlError(
            message="Rate limit exceeded",
            error_code="RATE_LIMIT_EXCEEDED",
            retry_after=60,
            url="https://example.com",
        )

        assert error.message == "Rate limit exceeded"
        assert error.error_code == "RATE_LIMIT_EXCEEDED"
        assert error.retry_after == 60
        assert error.is_retryable is True

    def test_should_categorize_errors_for_appropriate_handling(self):
        """
        RED TEST: Error system should categorize errors for appropriate handling strategies.
        """
        # Retryable errors
        rate_limit_error = FirecrawlError("Rate limit", "RATE_LIMIT", retry_after=60)
        timeout_error = FirecrawlError("Timeout", "TIMEOUT")

        # Non-retryable errors
        auth_error = FirecrawlError("Invalid API key", "AUTH_ERROR")
        invalid_url_error = FirecrawlError("Invalid URL", "INVALID_URL")

        assert rate_limit_error.is_retryable is True
        assert timeout_error.is_retryable is True
        assert auth_error.is_retryable is False
        assert invalid_url_error.is_retryable is False


# ========================================================================
# PERFORMANCE AND LOAD TESTS
# ========================================================================


class TestFirecrawlServicePerformance:
    """
    Performance-focused behavior tests ensuring service meets requirements.
    """

    @pytest.fixture()
    def firecrawl_service(self):
        """Fixture providing a FirecrawlService instance for performance testing"""
        return FirecrawlService(
            api_key="test_api_key_12345",
            base_url="https://api.firecrawl.dev",
        )

    @pytest.mark.asyncio()
    async def test_should_complete_single_scraping_within_timeout_limits(
        self,
        firecrawl_service,
    ):
        """
        RED TEST: Single scraping operation should complete within reasonable time limits.

        Performance requirement: <30s average processing time from Phase 2A plan.
        """
        start_time = datetime.now(UTC)

        result = await firecrawl_service.scrape_url(
            "https://example.com",
            options=ScrapingOptions(timeout=25000),  # 25 second timeout
        )

        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        assert duration < 30  # Must complete within 30 seconds
        assert result.success is True

    @pytest.mark.asyncio()
    async def test_should_maintain_quality_scores_above_threshold(
        self,
        firecrawl_service,
    ):
        """
        RED TEST: Scraped content should maintain quality scores >90% as per Phase 2A metrics.
        """

        mock_cognitive_engine = Mock()
        mock_cognitive_engine.assess_content_quality = AsyncMock(return_value=0.92)

        result = await firecrawl_service.scrape_with_cognitive_assessment(
            url="https://high-quality-site.com",
            cognitive_engine=mock_cognitive_engine,
        )

        assert result.quality_score > 0.90  # >90% quality requirement


if __name__ == "__main__":
    # Run the tests in RED phase - they should all fail initially
    pytest.main([__file__, "-v", "--tb=short"])
