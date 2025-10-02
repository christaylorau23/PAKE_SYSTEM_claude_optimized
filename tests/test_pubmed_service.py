#!/usr/bin/env python3
"""
PAKE System - Phase 2A TDD Tests for NCBI/PubMed E-utilities Service
Test-driven development for biomedical research paper ingestion.

Following CLAUDE.md TDD principles:
- RED: Write failing tests first (this file)
- GREEN: Minimal implementation to pass tests
- REFACTOR: Optimize and improve code structure

Based on NCBI E-utilities API documentation and best practices.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# These imports will fail initially (RED phase) - that's expected
try:
    from services.ingestion.pubmed_service import (
        PubMedAuthor,
        PubMedError,
        PubMedJournal,
        PubMedPaper,
        PubMedResult,
        PubMedSearchQuery,
        PubMedService,
    )

    from scripts.ingestion_pipeline import ContentItem
except ImportError:
    # Expected during RED phase - services don't exist yet
    pass


@dataclass
class MockPubMedResponse:
    """Mock response for testing PubMed E-utilities interactions"""

    status: int
    text: str
    success: bool = True


class TestPubMedService:
    """
    Test suite for PubMedService following behavior-driven testing principles.
    Tests focus on WHAT the service does, not HOW it does it.
    """

    @pytest.fixture()
    def pubmed_service(self):
        """Fixture providing a PubMedService instance for testing"""
        return PubMedService(
            base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
            email="test@example.com",
            api_key=None,  # Optional for testing
            max_results=100,
        )

    @pytest.fixture()
    def sample_search_query(self):
        """Fixture providing a sample PubMed search query"""
        return PubMedSearchQuery(
            terms=["machine learning", "artificial intelligence"],
            journal=["Nature", "Science"],
            authors=["Smith J", "Johnson M"],
            date_from=datetime(2023, 1, 1),
            date_to=datetime(2024, 12, 31),
            publication_types=["Journal Article", "Review"],
            mesh_terms=["Algorithms", "Computer Simulation"],
            max_results=50,
        )

    @pytest.fixture()
    def sample_pubmed_xml(self):
        """Fixture providing sample PubMed XML response"""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation Status="MEDLINE" Owner="NLM">
                    <PMID Version="1">12345678</PMID>
                    <DateCompleted>
                        <Year>2023</Year>
                        <Month>06</Month>
                        <Day>15</Day>
                    </DateCompleted>
                    <Article PubModel="Print">
                        <Journal>
                            <ISSN IssnType="Print">1234-5678</ISSN>
                            <JournalIssue CitedMedium="Print">
                                <Volume>45</Volume>
                                <Issue>3</Issue>
                                <PubDate>
                                    <Year>2023</Year>
                                    <Month>Mar</Month>
                                </PubDate>
                            </JournalIssue>
                            <Title>Journal of Machine Learning Research</Title>
                            <ISOAbbreviation>J Mach Learn Res</ISOAbbreviation>
                        </Journal>
                        <ArticleTitle>Deep Learning Applications in Medical Diagnosis</ArticleTitle>
                        <Pagination>
                            <MedlinePgn>123-145</MedlinePgn>
                        </Pagination>
                        <Abstract>
                            <AbstractText>This study explores the application of deep learning algorithms in medical diagnosis, demonstrating significant improvements in diagnostic accuracy and efficiency.</AbstractText>
                        </Abstract>
                        <AuthorList CompleteYN="Y">
                            <Author ValidYN="Y">
                                <LastName>Smith</LastName>
                                <ForeName>John</ForeName>
                                <Initials>J</Initials>
                                <AffiliationInfo>
                                    <Affiliation>Department of Computer Science, University of AI.</Affiliation>
                                </AffiliationInfo>
                            </Author>
                        </AuthorList>
                        <PublicationTypeList>
                            <PublicationType UI="D016428">Journal Article</PublicationType>
                        </PublicationTypeList>
                    </Article>
                    <MeshHeadingList>
                        <MeshHeading>
                            <DescriptorName UI="D000465" MajorTopicYN="Y">Algorithms</DescriptorName>
                        </MeshHeading>
                    </MeshHeadingList>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>"""

    # ========================================================================
    # BEHAVIOR TESTS - Core PubMed E-utilities Functionality
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_search_pubmed_with_advanced_query_parameters(
        self,
        pubmed_service,
        sample_search_query,
    ):
        """
        RED TEST: Service should support advanced PubMed search beyond basic queries.

        Must support MeSH terms, publication types, journals, author searches,
        and date ranges as per NCBI E-utilities specification.
        """
        result = await pubmed_service.search_papers(sample_search_query)

        assert result.success is True
        assert result.papers is not None
        assert len(result.papers) > 0
        assert result.total_results > 0
        assert result.query_used.terms == [
            "machine learning",
            "artificial intelligence",
        ]
        assert "Nature" in result.query_used.journal

    @pytest.mark.asyncio()
    async def test_should_parse_pubmed_xml_response_correctly(
        self,
        pubmed_service,
        sample_pubmed_xml,
    ):
        """
        RED TEST: Service should correctly parse PubMed XML responses.

        Critical for extracting PMID, title, abstract, authors, journal info,
        MeSH terms, and publication metadata.
        """
        result = await pubmed_service.parse_pubmed_response(sample_pubmed_xml)

        assert len(result.papers) == 1
        paper = result.papers[0]

        assert paper.pmid == "12345678"
        assert "Deep Learning Applications" in paper.title
        assert len(paper.authors) == 1
        assert paper.authors[0].last_name == "Smith"
        assert paper.journal.name == "Journal of Machine Learning Research"
        assert len(paper.mesh_terms) > 0
        assert "Algorithms" in paper.mesh_terms

    @pytest.mark.asyncio()
    async def test_should_support_mesh_term_searches(self, pubmed_service):
        """
        RED TEST: Service should support MeSH (Medical Subject Headings) term searches.

        MeSH terms are critical for precise biomedical literature searches.
        """
        mesh_query = PubMedSearchQuery(
            terms=["cancer treatment"],
            mesh_terms=["Neoplasms/therapy", "Drug Therapy"],
            max_results=20,
        )

        result = await pubmed_service.search_papers(mesh_query)

        assert result.success is True
        # Should find papers tagged with specified MeSH terms
        for paper in result.papers:
            assert any(
                "Neoplasms" in mesh or "Drug Therapy" in mesh
                for mesh in paper.mesh_terms
            )

    @pytest.mark.asyncio()
    async def test_should_support_publication_type_filtering(self, pubmed_service):
        """
        RED TEST: Service should filter by publication types (Review, Clinical Trial, etc).

        Essential for finding specific types of research publications.
        """
        review_query = PubMedSearchQuery(
            terms=["machine learning medical"],
            publication_types=["Review", "Systematic Review"],
            max_results=15,
        )

        result = await pubmed_service.search_papers(review_query)

        assert result.success is True
        # All results should be review articles
        for paper in result.papers:
            assert any("Review" in pub_type for pub_type in paper.publication_types)

    @pytest.mark.asyncio()
    async def test_should_support_journal_specific_searches(self, pubmed_service):
        """
        RED TEST: Service should support searching within specific journals.

        Important for tracking high-impact journal publications.
        """
        journal_query = PubMedSearchQuery(
            terms=["artificial intelligence"],
            journal=["Nature", "Science", "Cell"],
            date_from=datetime(2023, 1, 1),
            max_results=25,
        )

        result = await pubmed_service.search_papers(journal_query)

        assert result.success is True
        # Should find papers from specified journals
        found_journals = [paper.journal.name for paper in result.papers]
        assert any(
            journal in ["Nature", "Science", "Cell"] for journal in found_journals
        )

    @pytest.mark.asyncio()
    async def test_should_support_author_affiliation_searches(self, pubmed_service):
        """
        RED TEST: Service should support author and affiliation-based searches.

        Critical for tracking specific researchers and institutional research.
        """
        author_query = PubMedSearchQuery(
            terms=["deep learning"],
            authors=["Hinton G", "Bengio Y"],
            affiliations=["University of Toronto", "University of Montreal"],
            max_results=10,
        )

        result = await pubmed_service.search_papers(author_query)

        assert result.success is True
        # Should find papers by specified authors or affiliations
        found_authors = []
        found_affiliations = []
        for paper in result.papers:
            found_authors.extend(
                [f"{author.last_name} {author.initials}" for author in paper.authors],
            )
            found_affiliations.extend(
                [author.affiliation for author in paper.authors if author.affiliation],
            )

        assert any(
            "Hinton" in author or "Bengio" in author for author in found_authors
        ) or any(
            "Toronto" in affil or "Montreal" in affil for affil in found_affiliations
        )

    # ========================================================================
    # BEHAVIOR TESTS - E-utilities API Integration
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_use_esearch_and_efetch_apis_correctly(self, pubmed_service):
        """
        RED TEST: Service should use NCBI E-utilities ESearch and EFetch APIs correctly.

        Must follow the two-step process: ESearch for PMIDs, then EFetch for full records.
        """
        query = PubMedSearchQuery(terms=["machine learning"], max_results=5)

        with (
            patch.object(pubmed_service, "_esearch") as mock_esearch,
            patch.object(pubmed_service, "_efetch") as mock_efetch,
        ):
            mock_esearch.return_value = {
                "esearchresult": {"idlist": ["12345678", "87654321"], "count": "2"},
            }
            mock_efetch.return_value = """<PubmedArticleSet></PubmedArticleSet>"""

            result = await pubmed_service.search_papers(query)

            # Should call ESearch first, then EFetch
            mock_esearch.assert_called_once()
            mock_efetch.assert_called_once()

    @pytest.mark.asyncio()
    async def test_should_respect_ncbi_api_rate_limits(self, pubmed_service):
        """
        RED TEST: Service should respect NCBI API rate limits.

        Without API key: 3 requests/second
        With API key: 10 requests/second
        """
        query = PubMedSearchQuery(terms=["test"], max_results=5)

        # Mock rate-limited response
        with patch.object(pubmed_service, "_make_request") as mock_request:
            mock_request.return_value = MockPubMedResponse(
                status=429,
                text="Too Many Requests",
                success=False,
            )

            result = await pubmed_service.search_papers(query)

            assert result.success is False
            assert result.error is not None
            assert "rate limit" in result.error.message.lower()
            assert result.error.retry_after is not None

    @pytest.mark.asyncio()
    async def test_should_handle_large_result_sets_with_pagination(
        self,
        pubmed_service,
    ):
        """
        RED TEST: Service should handle large result sets using pagination.

        PubMed has limits on results per request, requiring pagination for large queries.
        """
        large_query = PubMedSearchQuery(
            terms=["cancer"],
            max_results=500,
            start=0,  # Larger than typical API limit
        )

        result = await pubmed_service.search_papers_paginated(
            large_query,
            page_size=100,
        )

        assert result.success is True
        assert len(result.papers) <= 500
        assert result.total_pages > 1
        assert result.current_page >= 0

    # ========================================================================
    # BEHAVIOR TESTS - Integration with Existing Pipeline
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_integrate_with_existing_content_pipeline(
        self,
        pubmed_service,
    ):
        """
        RED TEST: Service should integrate with existing ContentItem pipeline.

        Must convert PubMed papers to ContentItem format for pipeline processing.
        """
        query = PubMedSearchQuery(terms=["machine learning"], max_results=3)
        result = await pubmed_service.search_papers(query)

        content_items = await pubmed_service.to_content_items(result, "pubmed_research")

        assert len(content_items) > 0
        # Should be compatible with existing ContentItem structure
        for item in content_items:
            assert hasattr(item, "source_name")
            assert hasattr(item, "source_type")
            assert item.source_type == "pubmed_research"
            assert hasattr(item, "metadata")
            assert "pmid" in item.metadata
            assert "mesh_terms" in item.metadata

    @pytest.mark.asyncio()
    async def test_should_provide_enhanced_metadata_for_cognitive_analysis(
        self,
        pubmed_service,
        sample_search_query,
    ):
        """
        RED TEST: Service should provide rich metadata for cognitive analysis.

        Integration with autonomous cognitive system for research quality assessment.
        """
        result = await pubmed_service.search_papers(sample_search_query)

        # Should include metadata for cognitive processing
        assert result.papers[0].metadata is not None
        metadata = result.papers[0].metadata

        assert "mesh_terms" in metadata
        assert "publication_types" in metadata
        assert "journal_impact_factor" in metadata  # For relevance scoring
        assert "citation_count" in metadata
        assert "authors_affiliations" in metadata
        assert len(metadata["mesh_terms"]) > 0

    # ========================================================================
    # BEHAVIOR TESTS - Error Handling and Resilience
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_handle_invalid_pmids_gracefully(self, pubmed_service):
        """
        RED TEST: Service should handle invalid PMIDs without crashing.
        """
        query = PubMedSearchQuery(terms=["nonexistent pmid test"], max_results=5)

        result = await pubmed_service.search_papers(query)

        assert result.success is True
        assert result.papers == []  # No papers found for invalid search
        assert result.error is None

    @pytest.mark.asyncio()
    async def test_should_handle_malformed_xml_responses_gracefully(
        self,
        pubmed_service,
    ):
        """
        RED TEST: Service should handle malformed XML from NCBI APIs.

        Network issues or API changes can cause malformed responses.
        """
        malformed_xml = "<?xml version='1.0'?><invalid><unclosed>tag"

        result = await pubmed_service.parse_pubmed_response(malformed_xml)

        assert result.success is False
        assert result.error is not None
        assert "xml" in result.error.message.lower()
        assert result.papers == []

    @pytest.mark.asyncio()
    async def test_should_handle_ncbi_service_outages_gracefully(self, pubmed_service):
        """
        RED TEST: Service should handle NCBI service outages and timeouts.
        """
        query = PubMedSearchQuery(terms=["test"], max_results=5)

        with patch.object(pubmed_service, "_make_request") as mock_request:
            mock_request.return_value = MockPubMedResponse(
                status=503,
                text="Service Unavailable",
                success=False,
            )

            result = await pubmed_service.search_papers(query)

            assert result.success is False
            assert result.error is not None
            assert result.error.is_retryable is True

    # ========================================================================
    # BEHAVIOR TESTS - Performance and Caching
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_cache_recent_searches_for_performance(self, pubmed_service):
        """
        RED TEST: Service should cache recent searches to reduce API calls.

        Reduces load on NCBI servers and improves response times.
        """
        query = PubMedSearchQuery(terms=["caching test"], max_results=5)

        # First search - should hit API
        result1 = await pubmed_service.search_papers(query)

        # Second identical search - should use cache
        result2 = await pubmed_service.search_papers(query)

        assert result1.success is True
        assert result2.success is True
        assert result2.from_cache is True
        assert len(result1.papers) == len(result2.papers)

    @pytest.mark.asyncio()
    async def test_should_complete_searches_within_reasonable_time(
        self,
        pubmed_service,
    ):
        """
        RED TEST: PubMed searches should complete within reasonable time limits.

        Performance requirement: <45s average processing time for biomedical queries.
        """
        start_time = datetime.now(UTC)

        query = PubMedSearchQuery(terms=["performance test medical"], max_results=20)
        result = await pubmed_service.search_papers(query)

        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        assert duration < 45  # Must complete within 45 seconds
        assert result.success is True

    # ========================================================================
    # BEHAVIOR TESTS - Integration with Cognitive System
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_integrate_with_autonomous_cognitive_assessment(
        self,
        pubmed_service,
    ):
        """
        RED TEST: Service should integrate with cognitive system for paper quality assessment.

        Leveraging Phase 1 autonomous cognitive system for biomedical research relevance.
        """

        mock_cognitive_engine = Mock()
        mock_cognitive_engine.assess_research_quality = AsyncMock(return_value=0.92)

        query = PubMedSearchQuery(terms=["neural networks medical"], max_results=3)
        result = await pubmed_service.search_with_cognitive_assessment(
            query,
            cognitive_engine=mock_cognitive_engine,
        )

        assert result.success is True
        for paper in result.papers:
            assert paper.quality_score is not None
            assert paper.quality_score > 0.85
            assert paper.cognitive_assessment is not None

        mock_cognitive_engine.assess_research_quality.assert_called()

    @pytest.mark.asyncio()
    async def test_should_integrate_with_n8n_biomedical_workflows(self, pubmed_service):
        """
        RED TEST: Service should integrate with n8n biomedical research workflows.

        Must work with existing workflow automation for literature reviews.
        """

        mock_n8n_manager = Mock()
        mock_n8n_manager.trigger_workflow = AsyncMock(
            return_value={"workflow_id": "biomedical_001"},
        )

        query = PubMedSearchQuery(terms=["automated literature review"], max_results=5)
        result = await pubmed_service.search_papers(query)

        # Should be able to trigger biomedical processing workflow
        workflow_result = await pubmed_service.trigger_biomedical_workflow(
            result=result,
            n8n_manager=mock_n8n_manager,
            workflow_type="literature_review_analysis",
        )

        assert workflow_result["workflow_id"] is not None
        mock_n8n_manager.trigger_workflow.assert_called_once()

    # ========================================================================
    # BEHAVIOR TESTS - Data Structures and Immutability
    # ========================================================================

    def test_pubmed_paper_should_be_immutable(self):
        """
        RED TEST: PubMedPaper data structure should be immutable (frozen dataclass).

        Following functional programming principles from CLAUDE.md.
        """
        paper = PubMedPaper(
            pmid="12345678",
            title="Test Paper",
            authors=[],
            abstract="Test abstract",
            journal=PubMedJournal(name="Test Journal", issn="1234-5678"),
            publication_date=datetime.now(UTC),
            mesh_terms=["Test Term"],
            publication_types=["Journal Article"],
        )

        # Should not be able to modify paper after creation
        with pytest.raises(Exception):  # FrozenInstanceError expected
            paper.title = "Modified Title"

    def test_pubmed_search_query_should_have_sensible_defaults(self):
        """
        RED TEST: PubMedSearchQuery should provide sensible default values.
        """
        query = PubMedSearchQuery(terms=["test"])

        assert query.max_results > 0
        assert query.max_results <= 200  # PubMed reasonable limit
        assert query.start >= 0
        assert isinstance(query.sort_by, str)
        assert query.sort_order in ["ascending", "descending"]


# ========================================================================
# BEHAVIOR TESTS - Error Classes and Exception Handling
# ========================================================================


class TestPubMedErrorHandling:
    """
    Test suite for PubMedError classes and exception handling behaviors.
    """

    def test_pubmed_error_should_provide_structured_error_information(self):
        """
        RED TEST: PubMedError should provide structured error information.
        """
        error = PubMedError(
            message="NCBI API rate limit exceeded",
            error_code="RATE_LIMIT_EXCEEDED",
            retry_after=300,  # 5 minutes
            query="machine learning medical",
        )

        assert error.message == "NCBI API rate limit exceeded"
        assert error.error_code == "RATE_LIMIT_EXCEEDED"
        assert error.retry_after == 300
        assert error.is_retryable is True

    def test_should_categorize_pubmed_errors_appropriately(self):
        """
        RED TEST: Error system should categorize PubMed-specific errors.
        """
        # Retryable errors
        rate_limit_error = PubMedError("Rate limit", "RATE_LIMIT_EXCEEDED")
        network_error = PubMedError("Network timeout", "NETWORK_ERROR")
        service_error = PubMedError("Service unavailable", "SERVICE_UNAVAILABLE")

        # Non-retryable errors
        invalid_query_error = PubMedError("Invalid query syntax", "INVALID_QUERY")
        parse_error = PubMedError("XML parse error", "PARSE_ERROR")

        assert rate_limit_error.is_retryable is True
        assert network_error.is_retryable is True
        assert service_error.is_retryable is True
        assert invalid_query_error.is_retryable is False
        assert parse_error.is_retryable is False


# ========================================================================
# PERFORMANCE AND INTEGRATION TESTS
# ========================================================================


class TestPubMedServicePerformance:
    """
    Performance-focused behavior tests for PubMed service.
    """

    @pytest.fixture()
    def pubmed_service(self):
        """Fixture providing PubMedService for performance testing"""
        return PubMedService(max_results=50, email="test@example.com")

    @pytest.mark.asyncio()
    async def test_should_maintain_quality_scores_above_threshold(self, pubmed_service):
        """
        RED TEST: Biomedical research papers should maintain quality scores >85% as per Phase 2A metrics.
        """

        mock_cognitive_engine = Mock()
        mock_cognitive_engine.assess_research_quality = AsyncMock(return_value=0.91)

        query = PubMedSearchQuery(
            terms=["high quality biomedical research"],
            max_results=3,
        )
        result = await pubmed_service.search_with_cognitive_assessment(
            query,
            cognitive_engine=mock_cognitive_engine,
        )

        for paper in result.papers:
            assert paper.quality_score > 0.85  # >85% quality requirement for biomedical


if __name__ == "__main__":
    # Run the tests in RED phase - they should all fail initially
    pytest.main([__file__, "-v", "--tb=short"])
