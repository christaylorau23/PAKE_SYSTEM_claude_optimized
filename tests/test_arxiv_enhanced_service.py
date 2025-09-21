#!/usr/bin/env python3
"""
PAKE System - Phase 2A TDD Tests for Enhanced ArXiv API Service
Test-driven development for advanced academic paper ingestion.

Following CLAUDE.md TDD principles:
- RED: Write failing tests first (this file)
- GREEN: Minimal implementation to pass tests
- REFACTOR: Optimize and improve code structure

Based on Perplexity research for ArXiv API best practices.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# These imports will fail initially (RED phase) - that's expected
try:
    from scripts.ingestion_pipeline import ContentItem
    from services.ingestion.arxiv_enhanced_service import (
        ArxivEnhancedService,
        ArxivError,
        ArxivPaper,
        ArxivResult,
        ArxivSearchQuery,
    )
except ImportError:
    # Expected during RED phase - services don't exist yet
    pass


@dataclass
class MockArxivResponse:
    """Mock response for testing ArXiv API interactions"""

    status: int
    text: str
    success: bool = True


class TestArxivEnhancedService:
    """
    Test suite for ArxivEnhancedService following behavior-driven testing principles.
    Tests focus on WHAT the service does, not HOW it does it.
    """

    @pytest.fixture
    def arxiv_service(self):
        """Fixture providing an ArxivEnhancedService instance for testing"""
        return ArxivEnhancedService(
            base_url="http://export.arxiv.org/api/query",
            max_results=100,
        )

    @pytest.fixture
    def sample_search_query(self):
        """Fixture providing a sample search query"""
        return ArxivSearchQuery(
            terms=["machine learning", "neural networks"],
            categories=["cs.AI", "cs.LG"],
            authors=["Geoffrey Hinton"],
            date_from=datetime(2023, 1, 1),
            date_to=datetime(2024, 12, 31),
            max_results=50,
        )

    @pytest.fixture
    def sample_arxiv_xml(self):
        """Fixture providing sample ArXiv XML response"""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>ArXiv Query: search_query=machine+learning&amp;id_list=&amp;start=0&amp;max_results=1</title>
            <entry>
                <id>http://arxiv.org/abs/2301.00001v1</id>
                <updated>2023-01-01T12:00:00Z</updated>
                <published>2023-01-01T12:00:00Z</published>
                <title>Deep Learning Advances in Neural Architecture Search</title>
                <summary>This paper presents novel approaches to neural architecture search using deep learning techniques...</summary>
                <author>
                    <name>John Smith</name>
                </author>
                <author>
                    <name>Jane Doe</name>
                </author>
                <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.AI"/>
                <category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
                <category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
            </entry>
        </feed>"""

    # ========================================================================
    # BEHAVIOR TESTS - Core ArXiv API Functionality
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_search_arxiv_with_advanced_query_parameters(
        self,
        arxiv_service,
        sample_search_query,
    ):
        """
        RED TEST: Service should support advanced ArXiv search beyond basic RSS.

        Must support authors, categories, date ranges, and complex search terms
        as identified in Perplexity research.
        """
        # This test will fail initially - ArxivEnhancedService doesn't exist yet
        result = await arxiv_service.search_papers(sample_search_query)

        assert result.success is True
        assert result.papers is not None
        assert len(result.papers) > 0
        assert result.total_results > 0
        assert result.query_used.terms == ["machine learning", "neural networks"]
        assert "cs.AI" in result.query_used.categories

    @pytest.mark.asyncio
    async def test_should_parse_arxiv_xml_response_correctly(
        self,
        arxiv_service,
        sample_arxiv_xml,
    ):
        """
        RED TEST: Service should correctly parse ArXiv XML API responses.

        Critical for extracting paper metadata, authors, categories, and abstracts.
        """
        result = await arxiv_service.parse_arxiv_response(sample_arxiv_xml)

        assert len(result.papers) == 1
        paper = result.papers[0]

        assert paper.arxiv_id == "2301.00001v1"
        assert "Deep Learning Advances" in paper.title
        assert len(paper.authors) == 2
        assert "John Smith" in paper.authors
        assert "cs.AI" in paper.categories
        assert len(paper.abstract) > 50

    @pytest.mark.asyncio
    async def test_should_handle_complex_search_queries_with_boolean_logic(
        self,
        arxiv_service,
    ):
        """
        RED TEST: Service should support complex Boolean search queries.

        ArXiv API supports AND, OR, ANDNOT operators as per research.
        """
        complex_query = ArxivSearchQuery(
            terms=["(machine learning OR deep learning) AND neural networks"],
            categories=["cs.AI", "cs.LG", "stat.ML"],
            boolean_logic=True,
            max_results=25,
        )

        result = await arxiv_service.search_papers(complex_query)

        assert result.success is True
        assert result.papers is not None
        # Should handle complex query structure
        assert "(" in result.query_used.terms[0]
        assert "OR" in result.query_used.terms[0]

    @pytest.mark.asyncio
    async def test_should_support_author_specific_searches(self, arxiv_service):
        """
        RED TEST: Service should support targeted author searches.

        Important for following specific researchers' work.
        """
        author_query = ArxivSearchQuery(
            terms=["machine learning", "deep learning"],
            authors=["Yoshua Bengio", "Ian Goodfellow"],
            categories=["cs.AI"],
            date_from=datetime(2020, 1, 1),
            max_results=10,
        )

        result = await arxiv_service.search_papers(author_query)

        assert result.success is True
        # Should find papers by specified authors
        found_authors = []
        for paper in result.papers:
            found_authors.extend(paper.authors)

        assert any("Bengio" in author for author in found_authors) or any(
            "Goodfellow" in author for author in found_authors
        )

    @pytest.mark.asyncio
    async def test_should_support_date_range_filtering(self, arxiv_service):
        """
        RED TEST: Service should filter papers by publication date ranges.

        Essential for tracking recent research developments.
        """
        date_query = ArxivSearchQuery(
            terms=["transformer architecture"],
            date_from=datetime(2023, 1, 1, tzinfo=UTC),
            date_to=datetime(2023, 12, 31, tzinfo=UTC),
            max_results=20,
        )

        result = await arxiv_service.search_papers(date_query)

        assert result.success is True
        # All papers should be within date range
        for paper in result.papers:
            assert paper.published_date >= date_query.date_from
            assert paper.published_date <= date_query.date_to

    # ========================================================================
    # BEHAVIOR TESTS - Integration with Existing Pipeline
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_integrate_with_existing_rss_feed_system(self, arxiv_service):
        """
        RED TEST: Enhanced service should work alongside existing RSS feeds.

        Must complement, not replace, the current RSS ingestion.
        """
        # Should be able to use existing RSS categories
        rss_compatible_query = ArxivSearchQuery(
            # General terms for RSS compatibility
            terms=["artificial intelligence", "machine learning"],
            categories=["cs.AI", "cs.LG"],  # Same as RSS feeds
            max_results=10,
        )

        result = await arxiv_service.search_papers(rss_compatible_query)
        content_items = await arxiv_service.to_content_items(result, "arxiv_enhanced")

        assert len(content_items) > 0
        # Should be compatible with existing ContentItem structure
        for item in content_items:
            assert hasattr(item, "source_name")
            assert hasattr(item, "source_type")
            assert item.source_type == "arxiv_enhanced"
            assert hasattr(item, "metadata")

    @pytest.mark.asyncio
    async def test_should_provide_enhanced_metadata_for_cognitive_analysis(
        self,
        arxiv_service,
        sample_search_query,
    ):
        """
        RED TEST: Service should provide rich metadata for cognitive analysis.

        Integration with autonomous cognitive system for quality assessment.
        """
        result = await arxiv_service.search_papers(sample_search_query)

        # Should include metadata for cognitive processing
        assert result.papers[0].metadata is not None
        metadata = result.papers[0].metadata

        assert "categories" in metadata
        assert "citation_count" in metadata  # For relevance scoring
        assert "submission_history" in metadata
        assert "primary_category" in metadata
        assert len(metadata["authors_affiliations"]) > 0

    # ========================================================================
    # BEHAVIOR TESTS - Error Handling and Resilience
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_handle_arxiv_api_rate_limiting_gracefully(
        self,
        arxiv_service,
    ):
        """
        RED TEST: Service should handle ArXiv API rate limiting.

        ArXiv has specific rate limits that must be respected.
        """
        # Mock rate-limited response
        with patch.object(arxiv_service, "_make_arxiv_request") as mock_request:
            mock_request.return_value = MockArxivResponse(
                status=429,  # Too Many Requests
                text="Rate limit exceeded",
                success=False,
            )

            query = ArxivSearchQuery(terms=["test rate limit"], max_results=5)
            result = await arxiv_service.search_papers(query)

            assert result.success is False
            assert result.error is not None
            assert "rate limit" in result.error.message.lower()
            assert result.error.retry_after is not None

    @pytest.mark.asyncio
    async def test_should_handle_malformed_xml_responses_gracefully(
        self,
        arxiv_service,
    ):
        """
        RED TEST: Service should handle malformed XML from ArXiv API.

        Network issues or API changes can cause malformed responses.
        """
        malformed_xml = "<?xml version='1.0'?><invalid><unclosed>tag"

        result = await arxiv_service.parse_arxiv_response(malformed_xml)

        assert result.success is False
        assert result.error is not None
        assert "xml" in result.error.message.lower()
        assert result.papers == []

    @pytest.mark.asyncio
    async def test_should_handle_empty_search_results_gracefully(self, arxiv_service):
        """
        RED TEST: Service should handle empty search results without errors.
        """
        empty_query = ArxivSearchQuery(
            terms=["nonexistent_research_topic_12345"],
            max_results=10,
        )

        result = await arxiv_service.search_papers(empty_query)

        assert result.success is True
        assert result.papers == []
        assert result.total_results == 0
        assert result.error is None

    # ========================================================================
    # BEHAVIOR TESTS - Performance and Optimization
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_support_paginated_large_result_sets(self, arxiv_service):
        """
        RED TEST: Service should handle large result sets with pagination.

        Important for comprehensive research coverage.
        """
        large_query = ArxivSearchQuery(
            terms=["deep learning"],
            max_results=200,  # Larger than typical API limit
            start=0,
        )

        result = await arxiv_service.search_papers_paginated(large_query, page_size=50)

        assert result.success is True
        assert len(result.papers) <= 200
        assert result.total_pages > 1
        assert result.current_page >= 0

    @pytest.mark.asyncio
    async def test_should_cache_recent_searches_for_performance(self, arxiv_service):
        """
        RED TEST: Service should cache recent searches to improve performance.

        Reduces API calls and improves response times.
        """
        query = ArxivSearchQuery(terms=["caching test"], max_results=5)

        # First search - should hit API
        result1 = await arxiv_service.search_papers(query)

        # Second identical search - should use cache
        result2 = await arxiv_service.search_papers(query)

        assert result1.success is True
        assert result2.success is True
        assert result2.from_cache is True
        assert len(result1.papers) == len(result2.papers)

    # ========================================================================
    # BEHAVIOR TESTS - Integration with Cognitive System
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_integrate_with_autonomous_cognitive_assessment(
        self,
        arxiv_service,
    ):
        """
        RED TEST: Service should integrate with cognitive system for paper quality assessment.

        Leveraging Phase 1 autonomous cognitive system for research relevance.
        """

        mock_cognitive_engine = Mock()
        mock_cognitive_engine.assess_research_quality = AsyncMock(return_value=0.89)

        query = ArxivSearchQuery(terms=["neural networks"], max_results=3)
        result = await arxiv_service.search_with_cognitive_assessment(
            query,
            cognitive_engine=mock_cognitive_engine,
        )

        assert result.success is True
        for paper in result.papers:
            assert paper.quality_score is not None
            assert paper.quality_score > 0.8
            assert paper.cognitive_assessment is not None

        mock_cognitive_engine.assess_research_quality.assert_called()

    @pytest.mark.asyncio
    async def test_should_trigger_metacognitive_optimization_for_poor_searches(
        self,
        arxiv_service,
    ):
        """
        RED TEST: Service should use metacognitive optimization for poor search results.

        Integration with metacognitive engine to improve search strategies.
        """

        mock_metacognitive_engine = Mock()
        mock_metacognitive_engine.optimize_search_strategy = AsyncMock(
            return_value={
                "expanded_terms": ["machine learning", "ML", "artificial intelligence"],
                "additional_categories": ["stat.ML"],
                "date_expansion": 365,  # days
            },
        )

        poor_query = ArxivSearchQuery(terms=["obscure term"], max_results=5)

        result = await arxiv_service.search_with_optimization(
            poor_query,
            metacognitive_engine=mock_metacognitive_engine,
            min_results_threshold=3,
        )

        assert result.optimization_applied is True
        assert result.original_query != result.optimized_query
        assert len(result.optimized_query.terms) > len(poor_query.terms)

    # ========================================================================
    # BEHAVIOR TESTS - Data Structures and Immutability
    # ========================================================================

    def test_arxiv_paper_should_be_immutable(self):
        """
        RED TEST: ArxivPaper data structure should be immutable (frozen dataclass).

        Following functional programming principles from CLAUDE.md.
        """
        paper = ArxivPaper(
            arxiv_id="2301.00001",
            title="Test Paper",
            authors=["Test Author"],
            abstract="Test abstract",
            categories=["cs.AI"],
            published_date=datetime.now(UTC),
        )

        # Should not be able to modify paper after creation
        with pytest.raises(Exception):  # FrozenInstanceError expected
            paper.title = "Modified Title"

    def test_arxiv_search_query_should_have_sensible_defaults(self):
        """
        RED TEST: ArxivSearchQuery should provide sensible default values.
        """
        query = ArxivSearchQuery(terms=["test"])

        assert query.max_results > 0
        assert query.max_results <= 100  # ArXiv API limit
        assert query.start >= 0
        assert isinstance(query.boolean_logic, bool)
        assert isinstance(query.sort_by, str)
        assert query.sort_order in ["ascending", "descending"]

    # ========================================================================
    # BEHAVIOR TESTS - Integration with n8n Workflows
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_integrate_with_n8n_research_workflows(self, arxiv_service):
        """
        RED TEST: Service should integrate with n8n research automation workflows.

        Must work with existing workflow automation system.
        """

        mock_n8n_manager = Mock()
        mock_n8n_manager.trigger_workflow = AsyncMock(
            return_value={"workflow_id": "research_001"},
        )

        query = ArxivSearchQuery(terms=["automated research"], max_results=5)
        result = await arxiv_service.search_papers(query)

        # Should be able to trigger research processing workflow
        workflow_result = await arxiv_service.trigger_research_workflow(
            result=result,
            n8n_manager=mock_n8n_manager,
            workflow_type="research_paper_analysis",
        )

        assert workflow_result["workflow_id"] is not None
        mock_n8n_manager.trigger_workflow.assert_called_once()


# ========================================================================
# BEHAVIOR TESTS - Error Classes and Exception Handling
# ========================================================================


class TestArxivErrorHandling:
    """
    Test suite for ArxivError classes and exception handling behaviors.
    """

    def test_arxiv_error_should_provide_structured_error_information(self):
        """
        RED TEST: ArxivError should provide structured error information.
        """
        error = ArxivError(
            message="ArXiv API rate limit exceeded",
            error_code="RATE_LIMIT_EXCEEDED",
            retry_after=300,  # 5 minutes
            query="machine learning",
        )

        assert error.message == "ArXiv API rate limit exceeded"
        assert error.error_code == "RATE_LIMIT_EXCEEDED"
        assert error.retry_after == 300
        assert error.is_retryable is True

    def test_should_categorize_arxiv_errors_appropriately(self):
        """
        RED TEST: Error system should categorize ArXiv-specific errors.
        """
        # Retryable errors
        rate_limit_error = ArxivError("Rate limit", "RATE_LIMIT_EXCEEDED")
        network_error = ArxivError("Network timeout", "NETWORK_ERROR")

        # Non-retryable errors
        invalid_query_error = ArxivError("Invalid query syntax", "INVALID_QUERY")
        parse_error = ArxivError("XML parse error", "PARSE_ERROR")

        assert rate_limit_error.is_retryable is True
        assert network_error.is_retryable is True
        assert invalid_query_error.is_retryable is False
        assert parse_error.is_retryable is False


# ========================================================================
# PERFORMANCE AND INTEGRATION TESTS
# ========================================================================


class TestArxivServicePerformance:
    """
    Performance-focused behavior tests for ArXiv service.
    """

    @pytest.fixture
    def arxiv_service(self):
        """Fixture providing ArxivEnhancedService for performance testing"""
        return ArxivEnhancedService(max_results=50)

    @pytest.mark.asyncio
    async def test_should_complete_searches_within_reasonable_time(self, arxiv_service):
        """
        RED TEST: ArXiv searches should complete within reasonable time limits.

        Performance requirement: <30s average processing time from Phase 2A plan.
        """
        start_time = datetime.now(UTC)

        query = ArxivSearchQuery(terms=["performance test"], max_results=10)
        result = await arxiv_service.search_papers(query)

        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        assert duration < 30  # Must complete within 30 seconds
        assert result.success is True

    @pytest.mark.asyncio
    async def test_should_maintain_quality_scores_above_threshold(self, arxiv_service):
        """
        RED TEST: Research papers should maintain quality scores >90% as per Phase 2A metrics.
        """

        mock_cognitive_engine = Mock()
        mock_cognitive_engine.assess_research_quality = AsyncMock(return_value=0.94)

        query = ArxivSearchQuery(terms=["high quality research"], max_results=3)
        result = await arxiv_service.search_with_cognitive_assessment(
            query,
            cognitive_engine=mock_cognitive_engine,
        )

        for paper in result.papers:
            assert paper.quality_score > 0.90  # >90% quality requirement


if __name__ == "__main__":
    # Run the tests in RED phase - they should all fail initially
    pytest.main([__file__, "-v", "--tb=short"])
