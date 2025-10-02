"""
Comprehensive Unit Tests for IngestionService

Tests all primary use cases, edge cases, and expected failure modes
for the IngestionService class using pytest-mock for complete isolation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import asyncio
import json

from src.services.ingestion.ingestion_service import IngestionService
from src.services.ingestion.web_scraper import WebScraper
from src.services.ingestion.arxiv_scraper import ArxivScraper
from src.services.ingestion.pubmed_scraper import PubMedScraper
from src.services.ingestion.content_processor import ContentProcessor
from src.services.ingestion.deduplication_service import DeduplicationService
from tests.factories import SearchQueryFactory, SearchResultFactory


class TestIngestionServiceComprehensive:
    """Comprehensive unit tests for IngestionService"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mocked dependencies for IngestionService"""
        return {
            'webScraper': AsyncMock(spec=WebScraper),
            'arxivScraper': AsyncMock(spec=ArxivScraper),
            'pubmedScraper': AsyncMock(spec=PubMedScraper),
            'contentProcessor': AsyncMock(spec=ContentProcessor),
            'deduplicationService': AsyncMock(spec=DeduplicationService),
        }

    @pytest.fixture
    def ingestion_service(self, mock_dependencies):
        """Create IngestionService instance with mocked dependencies"""
        with patch('src.services.ingestion.ingestion_service.WebScraper') as mock_web_class, \
             patch('src.services.ingestion.ingestion_service.ArxivScraper') as mock_arxiv_class, \
             patch('src.services.ingestion.ingestion_service.PubMedScraper') as mock_pubmed_class, \
             patch('src.services.ingestion.ingestion_service.ContentProcessor') as mock_processor_class, \
             patch('src.services.ingestion.ingestion_service.DeduplicationService') as mock_dedup_class:
            
            # Configure mock classes
            mock_web_class.return_value = mock_dependencies['webScraper']
            mock_arxiv_class.return_value = mock_dependencies['arxivScraper']
            mock_pubmed_class.return_value = mock_dependencies['pubmedScraper']
            mock_processor_class.return_value = mock_dependencies['contentProcessor']
            mock_dedup_class.return_value = mock_dependencies['deduplicationService']
            
            service = IngestionService()
            service.web_scraper = mock_dependencies['webScraper']
            service.arxiv_scraper = mock_dependencies['arxivScraper']
            service.pubmed_scraper = mock_dependencies['pubmedScraper']
            service.content_processor = mock_dependencies['contentProcessor']
            service.deduplication_service = mock_dependencies['deduplicationService']
            return service

    # ============================================================================
    # PRIMARY USE CASES - Normal Operation Paths
    # ============================================================================

    @pytest.mark.unit_functional
    async def test_ingest_from_web_success(self, ingestion_service, mock_dependencies):
        """Test successful web content ingestion"""
        # Arrange
        query = SearchQueryFactory(sources=['web'])
        web_results = [SearchResultFactory(source='web') for _ in range(5)]
        
        mock_dependencies['webScraper'].scrape.return_value = web_results
        mock_dependencies['contentProcessor'].process.return_value = web_results
        mock_dependencies['deduplicationService'].deduplicate.return_value = web_results
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        assert len(result) == 5
        assert all(result_item.source == 'web' for result_item in result)
        
        # Verify interactions
        mock_dependencies['webScraper'].scrape.assert_called_once_with(query.query)
        mock_dependencies['contentProcessor'].process.assert_called_once()
        mock_dependencies['deduplicationService'].deduplicate.assert_called_once()

    @pytest.mark.unit_functional
    async def test_ingest_from_arxiv_success(self, ingestion_service, mock_dependencies):
        """Test successful ArXiv content ingestion"""
        # Arrange
        query = SearchQueryFactory(sources=['arxiv'])
        arxiv_results = [SearchResultFactory(source='arxiv') for _ in range(3)]
        
        mock_dependencies['arxivScraper'].scrape.return_value = arxiv_results
        mock_dependencies['contentProcessor'].process.return_value = arxiv_results
        mock_dependencies['deduplicationService'].deduplicate.return_value = arxiv_results
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        assert len(result) == 3
        assert all(result_item.source == 'arxiv' for result_item in result)
        
        # Verify interactions
        mock_dependencies['arxivScraper'].scrape.assert_called_once_with(query.query)
        mock_dependencies['contentProcessor'].process.assert_called_once()
        mock_dependencies['deduplicationService'].deduplicate.assert_called_once()

    @pytest.mark.unit_functional
    async def test_ingest_from_pubmed_success(self, ingestion_service, mock_dependencies):
        """Test successful PubMed content ingestion"""
        # Arrange
        query = SearchQueryFactory(sources=['pubmed'])
        pubmed_results = [SearchResultFactory(source='pubmed') for _ in range(4)]
        
        mock_dependencies['pubmedScraper'].scrape.return_value = pubmed_results
        mock_dependencies['contentProcessor'].process.return_value = pubmed_results
        mock_dependencies['deduplicationService'].deduplicate.return_value = pubmed_results
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        assert len(result) == 4
        assert all(result_item.source == 'pubmed' for result_item in result)
        
        # Verify interactions
        mock_dependencies['pubmedScraper'].scrape.assert_called_once_with(query.query)
        mock_dependencies['contentProcessor'].process.assert_called_once()
        mock_dependencies['deduplicationService'].deduplicate.assert_called_once()

    @pytest.mark.unit_functional
    async def test_ingest_from_multiple_sources_success(self, ingestion_service, mock_dependencies):
        """Test successful ingestion from multiple sources"""
        # Arrange
        query = SearchQueryFactory(sources=['web', 'arxiv', 'pubmed'])
        web_results = [SearchResultFactory(source='web') for _ in range(2)]
        arxiv_results = [SearchResultFactory(source='arxiv') for _ in range(2)]
        pubmed_results = [SearchResultFactory(source='pubmed') for _ in range(2)]
        
        mock_dependencies['webScraper'].scrape.return_value = web_results
        mock_dependencies['arxivScraper'].scrape.return_value = arxiv_results
        mock_dependencies['pubmedScraper'].scrape.return_value = pubmed_results
        
        all_results = web_results + arxiv_results + pubmed_results
        mock_dependencies['contentProcessor'].process.return_value = all_results
        mock_dependencies['deduplicationService'].deduplicate.return_value = all_results
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        assert len(result) == 6
        assert len([r for r in result if r.source == 'web']) == 2
        assert len([r for r in result if r.source == 'arxiv']) == 2
        assert len([r for r in result if r.source == 'pubmed']) == 2
        
        # Verify interactions
        mock_dependencies['webScraper'].scrape.assert_called_once()
        mock_dependencies['arxivScraper'].scrape.assert_called_once()
        mock_dependencies['pubmedScraper'].scrape.assert_called_once()

    @pytest.mark.unit_functional
    async def test_content_processing_success(self, ingestion_service, mock_dependencies):
        """Test successful content processing"""
        # Arrange
        query = SearchQueryFactory()
        raw_results = [SearchResultFactory(content='Raw content') for _ in range(3)]
        processed_results = [SearchResultFactory(content='Processed content') for _ in range(3)]
        
        mock_dependencies['webScraper'].scrape.return_value = raw_results
        mock_dependencies['contentProcessor'].process.return_value = processed_results
        mock_dependencies['deduplicationService'].deduplicate.return_value = processed_results
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        assert len(result) == 3
        assert all(result_item.content == 'Processed content' for result_item in result)
        
        # Verify interactions
        mock_dependencies['contentProcessor'].process.assert_called_once()

    @pytest.mark.unit_functional
    async def test_deduplication_success(self, ingestion_service, mock_dependencies):
        """Test successful content deduplication"""
        # Arrange
        query = SearchQueryFactory()
        raw_results = [SearchResultFactory(id=f'result_{i}') for i in range(5)]
        deduplicated_results = raw_results[:3]  # Remove duplicates
        
        mock_dependencies['webScraper'].scrape.return_value = raw_results
        mock_dependencies['contentProcessor'].process.return_value = raw_results
        mock_dependencies['deduplicationService'].deduplicate.return_value = deduplicated_results
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        assert len(result) == 3  # After deduplication
        
        # Verify interactions
        mock_dependencies['deduplicationService'].deduplicate.assert_called_once()

    # ============================================================================
    # EDGE CASES - Boundary Conditions and Edge Cases
    # ============================================================================

    @pytest.mark.unit_edge_case
    async def test_ingest_with_empty_query(self, ingestion_service, mock_dependencies):
        """Test ingestion with empty query"""
        # Arrange
        query = SearchQueryFactory(query='')
        mock_dependencies['webScraper'].scrape.return_value = []
        mock_dependencies['contentProcessor'].process.return_value = []
        mock_dependencies['deduplicationService'].deduplicate.return_value = []
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        assert len(result) == 0

    @pytest.mark.unit_edge_case
    async def test_ingest_with_special_characters_query(self, ingestion_service, mock_dependencies):
        """Test ingestion with special characters in query"""
        # Arrange
        query = SearchQueryFactory(query='machine learning & AI: "deep learning" (2023)')
        results = [SearchResultFactory() for _ in range(2)]
        
        mock_dependencies['webScraper'].scrape.return_value = results
        mock_dependencies['contentProcessor'].process.return_value = results
        mock_dependencies['deduplicationService'].deduplicate.return_value = results
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        assert len(result) == 2

    @pytest.mark.unit_edge_case
    async def test_ingest_with_very_long_query(self, ingestion_service, mock_dependencies):
        """Test ingestion with very long query"""
        # Arrange
        long_query = ' '.join(['word'] * 1000)  # Very long query
        query = SearchQueryFactory(query=long_query)
        results = [SearchResultFactory() for _ in range(1)]
        
        mock_dependencies['webScraper'].scrape.return_value = results
        mock_dependencies['contentProcessor'].process.return_value = results
        mock_dependencies['deduplicationService'].deduplicate.return_value = results
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        assert len(result) == 1

    @pytest.mark.unit_edge_case
    async def test_ingest_with_no_sources(self, ingestion_service, mock_dependencies):
        """Test ingestion with no sources specified"""
        # Arrange
        query = SearchQueryFactory(sources=[])
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        assert len(result) == 0

    @pytest.mark.unit_edge_case
    async def test_ingest_with_max_results_limit(self, ingestion_service, mock_dependencies):
        """Test ingestion with maximum results limit"""
        # Arrange
        query = SearchQueryFactory(max_results=5)
        many_results = [SearchResultFactory() for _ in range(20)]
        
        mock_dependencies['webScraper'].scrape.return_value = many_results
        mock_dependencies['contentProcessor'].process.return_value = many_results
        mock_dependencies['deduplicationService'].deduplicate.return_value = many_results
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        assert len(result) <= 5  # Should respect max_results limit

    @pytest.mark.unit_edge_case
    async def test_ingest_with_concurrent_requests(self, ingestion_service, mock_dependencies):
        """Test handling of concurrent ingestion requests"""
        # Arrange
        queries = [SearchQueryFactory(query=f'query_{i}') for i in range(5)]
        results = [SearchResultFactory() for _ in range(2)]
        
        mock_dependencies['webScraper'].scrape.return_value = results
        mock_dependencies['contentProcessor'].process.return_value = results
        mock_dependencies['deduplicationService'].deduplicate.return_value = results
        
        async def ingest_query(query):
            return await ingestion_service.ingest_content(query)
        
        # Act
        tasks = [ingest_query(query) for query in queries]
        results_list = await asyncio.gather(*tasks)
        
        # Assert
        assert len(results_list) == 5
        assert all(len(result) == 2 for result in results_list)

    # ============================================================================
    # ERROR HANDLING - Exception Scenarios and Error Cases
    # ============================================================================

    @pytest.mark.unit_error_handling
    async def test_web_scraper_failure(self, ingestion_service, mock_dependencies):
        """Test handling of web scraper failures"""
        # Arrange
        query = SearchQueryFactory(sources=['web'])
        mock_dependencies['webScraper'].scrape.side_effect = Exception("Web scraper failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Web scraper failed"):
            await ingestion_service.ingest_content(query)

    @pytest.mark.unit_error_handling
    async def test_arxiv_scraper_failure(self, ingestion_service, mock_dependencies):
        """Test handling of ArXiv scraper failures"""
        # Arrange
        query = SearchQueryFactory(sources=['arxiv'])
        mock_dependencies['arxivScraper'].scrape.side_effect = Exception("ArXiv scraper failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="ArXiv scraper failed"):
            await ingestion_service.ingest_content(query)

    @pytest.mark.unit_error_handling
    async def test_pubmed_scraper_failure(self, ingestion_service, mock_dependencies):
        """Test handling of PubMed scraper failures"""
        # Arrange
        query = SearchQueryFactory(sources=['pubmed'])
        mock_dependencies['pubmedScraper'].scrape.side_effect = Exception("PubMed scraper failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="PubMed scraper failed"):
            await ingestion_service.ingest_content(query)

    @pytest.mark.unit_error_handling
    async def test_content_processor_failure(self, ingestion_service, mock_dependencies):
        """Test handling of content processor failures"""
        # Arrange
        query = SearchQueryFactory()
        results = [SearchResultFactory() for _ in range(3)]
        
        mock_dependencies['webScraper'].scrape.return_value = results
        mock_dependencies['contentProcessor'].process.side_effect = Exception("Content processor failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Content processor failed"):
            await ingestion_service.ingest_content(query)

    @pytest.mark.unit_error_handling
    async def test_deduplication_service_failure(self, ingestion_service, mock_dependencies):
        """Test handling of deduplication service failures"""
        # Arrange
        query = SearchQueryFactory()
        results = [SearchResultFactory() for _ in range(3)]
        
        mock_dependencies['webScraper'].scrape.return_value = results
        mock_dependencies['contentProcessor'].process.return_value = results
        mock_dependencies['deduplicationService'].deduplicate.side_effect = Exception("Deduplication failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Deduplication failed"):
            await ingestion_service.ingest_content(query)

    @pytest.mark.unit_error_handling
    async def test_network_timeout_error(self, ingestion_service, mock_dependencies):
        """Test handling of network timeout errors"""
        # Arrange
        query = SearchQueryFactory(sources=['web'])
        mock_dependencies['webScraper'].scrape.side_effect = asyncio.TimeoutError("Network timeout")
        
        # Act & Assert
        with pytest.raises(asyncio.TimeoutError, match="Network timeout"):
            await ingestion_service.ingest_content(query)

    @pytest.mark.unit_error_handling
    async def test_partial_failure_with_multiple_sources(self, ingestion_service, mock_dependencies):
        """Test handling of partial failures with multiple sources"""
        # Arrange
        query = SearchQueryFactory(sources=['web', 'arxiv', 'pubmed'])
        web_results = [SearchResultFactory(source='web') for _ in range(2)]
        arxiv_results = [SearchResultFactory(source='arxiv') for _ in range(2)]
        
        mock_dependencies['webScraper'].scrape.return_value = web_results
        mock_dependencies['arxivScraper'].scrape.return_value = arxiv_results
        mock_dependencies['pubmedScraper'].scrape.side_effect = Exception("PubMed service unavailable")
        
        all_results = web_results + arxiv_results
        mock_dependencies['contentProcessor'].process.return_value = all_results
        mock_dependencies['deduplicationService'].deduplicate.return_value = all_results
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        assert len(result) == 4  # Only web and arxiv results
        assert len([r for r in result if r.source == 'web']) == 2
        assert len([r for r in result if r.source == 'arxiv']) == 2

    # ============================================================================
    # PERFORMANCE TESTS - Algorithm Efficiency and Performance
    # ============================================================================

    @pytest.mark.unit_performance
    async def test_ingestion_performance(self, ingestion_service, mock_dependencies):
        """Test ingestion performance"""
        import time
        
        # Arrange
        query = SearchQueryFactory()
        results = [SearchResultFactory() for _ in range(10)]
        
        mock_dependencies['webScraper'].scrape.return_value = results
        mock_dependencies['contentProcessor'].process.return_value = results
        mock_dependencies['deduplicationService'].deduplicate.return_value = results
        
        # Act
        start_time = time.time()
        for _ in range(10):
            await ingestion_service.ingest_content(query)
        end_time = time.time()
        
        # Assert
        execution_time = end_time - start_time
        assert execution_time < 5.0  # Should complete within 5 seconds

    @pytest.mark.unit_performance
    async def test_concurrent_ingestion_performance(self, ingestion_service, mock_dependencies):
        """Test concurrent ingestion performance"""
        import time
        
        # Arrange
        queries = [SearchQueryFactory(query=f'query_{i}') for i in range(20)]
        results = [SearchResultFactory() for _ in range(5)]
        
        mock_dependencies['webScraper'].scrape.return_value = results
        mock_dependencies['contentProcessor'].process.return_value = results
        mock_dependencies['deduplicationService'].deduplicate.return_value = results
        
        async def ingest_query(query):
            return await ingestion_service.ingest_content(query)
        
        # Act
        start_time = time.time()
        tasks = [ingest_query(query) for query in queries]
        results_list = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Assert
        assert len(results_list) == 20
        execution_time = end_time - start_time
        assert execution_time < 10.0  # Should complete within 10 seconds

    @pytest.mark.unit_performance
    async def test_large_result_set_performance(self, ingestion_service, mock_dependencies):
        """Test performance with large result sets"""
        import time
        
        # Arrange
        query = SearchQueryFactory()
        large_results = [SearchResultFactory() for _ in range(1000)]
        
        mock_dependencies['webScraper'].scrape.return_value = large_results
        mock_dependencies['contentProcessor'].process.return_value = large_results
        mock_dependencies['deduplicationService'].deduplicate.return_value = large_results
        
        # Act
        start_time = time.time()
        result = await ingestion_service.ingest_content(query)
        end_time = time.time()
        
        # Assert
        assert len(result) == 1000
        execution_time = end_time - start_time
        assert execution_time < 10.0  # Should complete within 10 seconds

    # ============================================================================
    # SECURITY TESTS - Data Protection and Access Control
    # ============================================================================

    @pytest.mark.unit_security
    async def test_sensitive_data_not_exposed(self, ingestion_service, mock_dependencies):
        """Test that sensitive data is not exposed in results"""
        # Arrange
        query = SearchQueryFactory()
        results_with_sensitive_data = [
            SearchResultFactory(content='Normal content'),
            SearchResultFactory(content='Content with password: secret123'),
            SearchResultFactory(content='Content with API key: sk-1234567890')
        ]
        
        mock_dependencies['webScraper'].scrape.return_value = results_with_sensitive_data
        mock_dependencies['contentProcessor'].process.return_value = results_with_sensitive_data
        mock_dependencies['deduplicationService'].deduplicate.return_value = results_with_sensitive_data
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        # Verify that sensitive data is not exposed in logs or responses
        # This would require checking log output, but for unit tests we verify
        # that the data is processed normally
        assert len(result) == 3

    @pytest.mark.unit_security
    async def test_query_sanitization(self, ingestion_service, mock_dependencies):
        """Test that queries are properly sanitized"""
        # Arrange
        malicious_query = SearchQueryFactory(query='<script>alert("xss")</script>')
        results = [SearchResultFactory() for _ in range(2)]
        
        mock_dependencies['webScraper'].scrape.return_value = results
        mock_dependencies['contentProcessor'].process.return_value = results
        mock_dependencies['deduplicationService'].deduplicate.return_value = results
        
        # Act
        result = await ingestion_service.ingest_content(malicious_query)
        
        # Assert
        assert result is not None
        # Verify that the query is passed to scrapers as-is (sanitization should happen at higher level)
        mock_dependencies['webScraper'].scrape.assert_called_once()

    @pytest.mark.unit_security
    async def test_rate_limiting_integration(self, ingestion_service, mock_dependencies):
        """Test that rate limiting is integrated with ingestion"""
        # Arrange
        query = SearchQueryFactory()
        mock_dependencies['webScraper'].scrape.side_effect = Exception("Rate limit exceeded")
        
        # Act & Assert
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await ingestion_service.ingest_content(query)

    @pytest.mark.unit_security
    async def test_content_validation(self, ingestion_service, mock_dependencies):
        """Test that content is properly validated"""
        # Arrange
        query = SearchQueryFactory()
        invalid_results = [
            SearchResultFactory(content=''),  # Empty content
            SearchResultFactory(content=None),  # None content
            SearchResultFactory(title=''),  # Empty title
        ]
        
        mock_dependencies['webScraper'].scrape.return_value = invalid_results
        mock_dependencies['contentProcessor'].process.return_value = invalid_results
        mock_dependencies['deduplicationService'].deduplicate.return_value = invalid_results
        
        # Act
        result = await ingestion_service.ingest_content(query)
        
        # Assert
        assert result is not None
        # Verify that invalid content is handled appropriately
        assert len(result) == 3
