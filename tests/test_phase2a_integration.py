#!/usr/bin/env python3
"""
PAKE System - Phase 2A Integration Tests
Comprehensive integration testing for all Phase 2A omni-source ingestion services.

Tests the complete pipeline from multiple sources through cognitive processing
to final content integration.

Following CLAUDE.md TDD principles for integration testing.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from scripts.ingestion_pipeline import ContentItem
from services.ingestion.arxiv_enhanced_service import (
    ArxivEnhancedService,
    ArxivSearchQuery,
)

# Import all Phase 2A services
from services.ingestion.firecrawl_service import (
    FirecrawlService,
    ScrapingOptions,
)
from services.ingestion.pubmed_service import PubMedSearchQuery, PubMedService


class TestPhase2AIntegration:
    """
    Integration test suite for Phase 2A omni-source ingestion pipeline.
    Tests focus on end-to-end workflows and service interactions.
    """

    @pytest.fixture
    def mock_cognitive_engine(self):
        """Mock cognitive engine for testing"""
        engine = Mock()
        engine.assess_research_quality = AsyncMock(return_value=0.89)
        engine.assess_content_quality = AsyncMock(return_value=0.92)
        engine.categorize_content = AsyncMock(return_value=["AI", "Machine Learning"])
        engine.extract_insights = AsyncMock(
            return_value={
                "key_concepts": ["neural networks", "deep learning"],
                "relevance_score": 0.94,
                "complexity_level": "advanced",
            },
        )
        return engine

    @pytest.fixture
    def mock_n8n_manager(self):
        """Mock n8n workflow manager for testing"""
        manager = Mock()
        manager.trigger_workflow = AsyncMock(
            return_value={"workflow_id": "integration_001"},
        )
        manager.monitor_workflow = AsyncMock(return_value={"status": "completed"})
        return manager

    @pytest.fixture
    def firecrawl_service(self):
        """Firecrawl service instance"""
        return FirecrawlService(
            api_key="test-key",
            base_url="https://api.firecrawl.dev",
        )

    @pytest.fixture
    def arxiv_service(self):
        """ArXiv enhanced service instance"""
        return ArxivEnhancedService(
            base_url="http://export.arxiv.org/api/query",
            max_results=50,
        )

    @pytest.fixture
    def pubmed_service(self):
        """PubMed E-utilities service instance"""
        return PubMedService(email="test@example.com", max_results=50)

    # ========================================================================
    # INTEGRATION TESTS - Multi-Source Content Ingestion
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_orchestrate_multi_source_research_ingestion(
        self,
        firecrawl_service,
        arxiv_service,
        pubmed_service,
        mock_cognitive_engine,
    ):
        """
        Integration test: Should orchestrate content ingestion from multiple sources
        for a comprehensive research topic.

        Tests the complete pipeline: Web scraping + Academic papers + Biomedical research
        """
        research_topic = "machine learning applications in healthcare"

        # 1. Scrape relevant web content
        web_urls = [
            "https://example.com/ml-healthcare-overview",
            "https://example.com/ai-medical-diagnosis",
        ]

        web_results = []
        for url in web_urls:
            result = await firecrawl_service.scrape_url(
                url,
                options=ScrapingOptions(
                    wait_time=3000,
                    include_headings=True,
                    include_links=True,
                ),
            )
            assert result.success
            web_results.append(result)

        # 2. Search academic papers
        arxiv_query = ArxivSearchQuery(
            terms=["machine learning", "healthcare", "medical AI"],
            categories=["cs.AI", "cs.LG"],
            max_results=10,
        )

        arxiv_result = await arxiv_service.search_with_cognitive_assessment(
            arxiv_query,
            cognitive_engine=mock_cognitive_engine,
        )

        assert arxiv_result.success
        assert len(arxiv_result.papers) > 0

        # 3. Search biomedical research
        pubmed_query = PubMedSearchQuery(
            terms=["machine learning", "artificial intelligence"],
            mesh_terms=["Algorithms"],  # Use MeSH term that exists in mock data
            publication_types=["Journal Article", "Review"],
            max_results=10,
        )

        pubmed_result = await pubmed_service.search_with_cognitive_assessment(
            pubmed_query,
            cognitive_engine=mock_cognitive_engine,
        )

        assert pubmed_result.success
        assert len(pubmed_result.papers) > 0

        # 4. Verify cognitive assessment was applied to all sources
        for paper in arxiv_result.papers:
            assert paper.quality_score is not None
            assert paper.quality_score > 0.8

        for paper in pubmed_result.papers:
            assert paper.quality_score is not None
            assert paper.quality_score > 0.8

        # 5. Verify cross-source content diversity
        total_sources = (
            len(web_results) + len(arxiv_result.papers) + len(pubmed_result.papers)
        )
        assert total_sources >= 5  # Should have diverse content from all sources

    @pytest.mark.asyncio
    async def test_should_integrate_all_services_with_content_pipeline(
        self,
        firecrawl_service,
        arxiv_service,
        pubmed_service,
    ):
        """
        Integration test: Should convert all service results to unified ContentItem format
        for pipeline processing.
        """
        # Collect content from all sources
        all_content_items = []

        # 1. Web content
        web_result = await firecrawl_service.scrape_url("https://example.com/test")
        if web_result.success:
            web_content = await firecrawl_service.to_content_item(
                web_result,
                "web_research",
            )
            all_content_items.append(web_content)

        # 2. ArXiv papers
        arxiv_query = ArxivSearchQuery(terms=["neural networks"], max_results=3)
        arxiv_result = await arxiv_service.search_papers(arxiv_query)
        if arxiv_result.success:
            arxiv_content = await arxiv_service.to_content_items(
                arxiv_result,
                "arxiv_research",
            )
            all_content_items.extend(arxiv_content)

        # 3. PubMed papers
        pubmed_query = PubMedSearchQuery(terms=["deep learning"], max_results=3)
        pubmed_result = await pubmed_service.search_papers(pubmed_query)
        if pubmed_result.success:
            pubmed_content = await pubmed_service.to_content_items(
                pubmed_result,
                "pubmed_research",
            )
            all_content_items.extend(pubmed_content)

        # Verify unified format
        assert len(all_content_items) > 0

        for item in all_content_items:
            assert isinstance(item, ContentItem)
            assert hasattr(item, "source_name")
            assert hasattr(item, "source_type")
            assert hasattr(item, "title")
            assert hasattr(item, "content")
            assert hasattr(item, "metadata")
            assert item.source_type in [
                "firecrawl_web",
                "arxiv_enhanced",
                "pubmed_research",
            ]

    # ========================================================================
    # INTEGRATION TESTS - Cognitive Processing Pipeline
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_apply_unified_cognitive_assessment_across_sources(
        self,
        arxiv_service,
        pubmed_service,
        mock_cognitive_engine,
    ):
        """
        Integration test: Should apply consistent cognitive assessment
        across all content sources.
        """
        # Search both sources with cognitive assessment
        arxiv_query = ArxivSearchQuery(terms=["artificial intelligence"], max_results=3)
        pubmed_query = PubMedSearchQuery(
            terms=["artificial intelligence"],
            max_results=3,
        )

        # Apply cognitive assessment to both
        arxiv_result = await arxiv_service.search_with_cognitive_assessment(
            arxiv_query,
            cognitive_engine=mock_cognitive_engine,
        )

        pubmed_result = await pubmed_service.search_with_cognitive_assessment(
            pubmed_query,
            cognitive_engine=mock_cognitive_engine,
        )

        # Verify consistent quality assessment
        all_quality_scores = []

        if arxiv_result.success:
            for paper in arxiv_result.papers:
                assert paper.quality_score is not None
                assert paper.cognitive_assessment is not None
                all_quality_scores.append(paper.quality_score)

        if pubmed_result.success:
            for paper in pubmed_result.papers:
                assert paper.quality_score is not None
                assert paper.cognitive_assessment is not None
                all_quality_scores.append(paper.quality_score)

        # Verify cognitive engine was called consistently
        total_assessments = len(arxiv_result.papers) + len(pubmed_result.papers)
        assert (
            mock_cognitive_engine.assess_research_quality.call_count
            == total_assessments
        )

        # Verify quality threshold compliance
        assert all(score > 0.85 for score in all_quality_scores)

    @pytest.mark.asyncio
    async def test_should_handle_mixed_content_quality_filtering(
        self,
        arxiv_service,
        pubmed_service,
        mock_cognitive_engine,
    ):
        """
        Integration test: Should filter content based on cognitive quality assessment
        across different source types.
        """
        # Mock varied quality scores
        quality_scores = [0.95, 0.72, 0.88, 0.65, 0.91]  # Mixed quality
        mock_cognitive_engine.assess_research_quality = AsyncMock(
            side_effect=quality_scores,
        )

        # Search multiple sources
        arxiv_query = ArxivSearchQuery(terms=["machine learning"], max_results=3)
        pubmed_query = PubMedSearchQuery(terms=["machine learning"], max_results=2)

        arxiv_result = await arxiv_service.search_with_cognitive_assessment(
            arxiv_query,
            cognitive_engine=mock_cognitive_engine,
        )

        pubmed_result = await pubmed_service.search_with_cognitive_assessment(
            pubmed_query,
            cognitive_engine=mock_cognitive_engine,
        )

        # Filter high-quality content (>0.8)
        high_quality_content = []

        if arxiv_result.success:
            high_quality_content.extend(
                [
                    paper
                    for paper in arxiv_result.papers
                    if paper.quality_score and paper.quality_score > 0.8
                ],
            )

        if pubmed_result.success:
            high_quality_content.extend(
                [
                    paper
                    for paper in pubmed_result.papers
                    if paper.quality_score and paper.quality_score > 0.8
                ],
            )

        # Should have filtered to high-quality content only
        assert len(high_quality_content) >= 2
        assert all(paper.quality_score > 0.8 for paper in high_quality_content)

    # ========================================================================
    # INTEGRATION TESTS - Workflow Automation
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_integrate_with_n8n_research_automation_workflows(
        self,
        arxiv_service,
        pubmed_service,
        mock_n8n_manager,
    ):
        """
        Integration test: Should trigger appropriate n8n workflows
        based on content source and type.
        """
        # Search different types of content
        arxiv_query = ArxivSearchQuery(terms=["automated research"], max_results=2)
        pubmed_query = PubMedSearchQuery(terms=["clinical trials"], max_results=2)

        arxiv_result = await arxiv_service.search_papers(arxiv_query)
        pubmed_result = await pubmed_service.search_papers(pubmed_query)

        # Trigger different workflows based on source
        workflows_triggered = []

        if arxiv_result.success:
            arxiv_workflow = await arxiv_service.trigger_research_workflow(
                result=arxiv_result,
                n8n_manager=mock_n8n_manager,
                workflow_type="arxiv_paper_analysis",
            )
            workflows_triggered.append(arxiv_workflow)

        if pubmed_result.success:
            pubmed_workflow = await pubmed_service.trigger_biomedical_workflow(
                result=pubmed_result,
                n8n_manager=mock_n8n_manager,
                workflow_type="biomedical_literature_review",
            )
            workflows_triggered.append(pubmed_workflow)

        # Verify workflows were triggered appropriately
        assert len(workflows_triggered) >= 2
        assert all(
            workflow["workflow_id"] is not None for workflow in workflows_triggered
        )
        assert mock_n8n_manager.trigger_workflow.call_count >= 2

    @pytest.mark.asyncio
    async def test_should_handle_cross_source_content_deduplication(
        self,
        arxiv_service,
        pubmed_service,
    ):
        """
        Integration test: Should identify and handle potential content duplication
        across different sources.
        """
        # Search for similar content across both sources
        search_term = "deep learning medical imaging"

        arxiv_query = ArxivSearchQuery(
            terms=[search_term],
            categories=["cs.CV", "cs.LG"],
            max_results=5,
        )

        pubmed_query = PubMedSearchQuery(
            terms=["deep learning", "medical imaging"],
            mesh_terms=["Algorithms"],  # Use MeSH term that exists in mock data
            max_results=5,
        )

        arxiv_result = await arxiv_service.search_papers(arxiv_query)
        pubmed_result = await pubmed_service.search_papers(pubmed_query)

        # Convert to unified format for comparison
        all_content = []

        if arxiv_result.success:
            arxiv_content = await arxiv_service.to_content_items(
                arxiv_result,
                "arxiv_research",
            )
            all_content.extend(arxiv_content)

        if pubmed_result.success:
            pubmed_content = await pubmed_service.to_content_items(
                pubmed_result,
                "pubmed_research",
            )
            all_content.extend(pubmed_content)

        # Basic deduplication check (by title similarity)
        titles = [item.title.lower() for item in all_content]
        unique_titles = set(titles)

        # Should have content from both sources
        assert len(all_content) >= 2  # Adjust for realistic mock data

        # Content should be reasonably diverse
        diversity_ratio = len(unique_titles) / len(all_content)
        assert diversity_ratio > 0.7  # At least 70% unique content

    # ========================================================================
    # INTEGRATION TESTS - Performance and Scalability
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_handle_concurrent_multi_source_ingestion(
        self,
        firecrawl_service,
        arxiv_service,
        pubmed_service,
        mock_cognitive_engine,
    ):
        """
        Integration test: Should handle concurrent ingestion from multiple sources
        without performance degradation.
        """
        start_time = datetime.now(UTC)

        # Define concurrent search tasks
        tasks = []

        # Web scraping task
        web_task = firecrawl_service.scrape_url(
            "https://example.com/concurrent-test",
            options=ScrapingOptions(wait_time=3000),
        )
        tasks.append(web_task)

        # ArXiv search task
        arxiv_query = ArxivSearchQuery(terms=["concurrent processing"], max_results=3)
        arxiv_task = arxiv_service.search_with_cognitive_assessment(
            arxiv_query,
            cognitive_engine=mock_cognitive_engine,
        )
        tasks.append(arxiv_task)

        # PubMed search task
        pubmed_query = PubMedSearchQuery(terms=["parallel processing"], max_results=3)
        pubmed_task = pubmed_service.search_with_cognitive_assessment(
            pubmed_query,
            cognitive_engine=mock_cognitive_engine,
        )
        tasks.append(pubmed_task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = datetime.now(UTC)
        total_duration = (end_time - start_time).total_seconds()

        # Verify all tasks completed successfully
        assert len(results) == 3

        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 2  # At least 2 should succeed

        # Performance requirement: Should complete within reasonable time
        assert total_duration < 60  # Should complete within 1 minute

        # Verify results quality
        for result in successful_results:
            if hasattr(result, "success"):
                assert result.success

    @pytest.mark.asyncio
    async def test_should_maintain_system_stability_under_load(
        self,
        arxiv_service,
        pubmed_service,
        mock_cognitive_engine,
    ):
        """
        Integration test: Should maintain system stability under higher load
        with proper error handling and resource management.
        """
        # Simulate higher load with multiple concurrent searches
        search_tasks = []

        # Create multiple ArXiv searches
        for i in range(5):
            query = ArxivSearchQuery(terms=[f"load test {i}"], max_results=2)
            task = arxiv_service.search_with_cognitive_assessment(
                query,
                cognitive_engine=mock_cognitive_engine,
            )
            search_tasks.append(task)

        # Create multiple PubMed searches
        for i in range(5):
            query = PubMedSearchQuery(terms=[f"stress test {i}"], max_results=2)
            task = pubmed_service.search_with_cognitive_assessment(
                query,
                cognitive_engine=mock_cognitive_engine,
            )
            search_tasks.append(task)

        # Execute all searches concurrently
        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Verify system handled load gracefully
        successful_results = [
            r for r in results if not isinstance(r, Exception) and r.success
        ]
        failed_results = [
            r for r in results if isinstance(r, Exception) or not r.success
        ]

        # Should have high success rate even under load
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.8  # At least 80% success rate

        # Verify cognitive engine was called appropriately
        total_papers = sum(
            len(result.papers)
            for result in successful_results
            if hasattr(result, "papers")
        )
        if total_papers > 0:
            assert (
                mock_cognitive_engine.assess_research_quality.call_count == total_papers
            )

    # ========================================================================
    # INTEGRATION TESTS - Error Handling and Resilience
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_handle_partial_service_failures_gracefully(
        self,
        arxiv_service,
        pubmed_service,
        mock_cognitive_engine,
    ):
        """
        Integration test: Should handle partial service failures
        and continue processing with available services.
        """
        # Mock one service to fail
        with patch.object(arxiv_service, "search_papers") as mock_arxiv:
            mock_arxiv.return_value = AsyncMock(
                success=False,
                error="Service unavailable",
            )

            # Attempt multi-source search
            arxiv_query = ArxivSearchQuery(terms=["failure test"], max_results=3)
            pubmed_query = PubMedSearchQuery(terms=["resilience test"], max_results=3)

            arxiv_result = await arxiv_service.search_with_cognitive_assessment(
                arxiv_query,
                cognitive_engine=mock_cognitive_engine,
            )

            pubmed_result = await pubmed_service.search_with_cognitive_assessment(
                pubmed_query,
                cognitive_engine=mock_cognitive_engine,
            )

            # Should handle ArXiv failure gracefully
            assert not arxiv_result.success

            # PubMed should still work
            assert pubmed_result.success
            assert len(pubmed_result.papers) > 0

            # System should continue with available services
            available_content = []
            if pubmed_result.success:
                available_content.extend(pubmed_result.papers)

            assert len(available_content) > 0


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])
