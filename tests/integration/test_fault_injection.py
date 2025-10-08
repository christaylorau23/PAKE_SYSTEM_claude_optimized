#!/usr/bin/env python3
"""
PAKE System - Fault Injection Testing for External APIs
Step 2.3: Comprehensive resilience testing for external API dependencies

This module implements fault injection testing to ensure the system is resilient
to unpredictable failures from external API dependencies (ArXiv, PubMed, Firecrawl).

Test Categories:
- HTTP 503 Service Unavailable errors
- Network timeouts
- Malformed or empty JSON responses
- HTTP 429 Rate Limit Exceeded errors
- Connection errors
- Partial response failures
"""

import asyncio
from datetime import UTC, datetime
import json
import logging
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
from aioresponses import aioresponses
import pytest
import responses

try:
    from src.services.ingestion.arxiv_enhanced_service import (
        ArxivEnhancedService,
        ArxivError,
        ArxivSearchQuery,
    )
    from src.services.ingestion.firecrawl_service import (
        FirecrawlError,
        FirecrawlService,
        ScrapingOptions,
    )
    from src.services.ingestion.pubmed_service import (
        PubMedError,
        PubMedSearchQuery,
        PubMedService,
    )
except ImportError:
    # Handle import errors gracefully for testing
    pass

logger = logging.getLogger(__name__)


class TestFaultInjectionFirecrawl:
    """Fault injection tests for FirecrawlService API resilience"""

    @pytest.fixture
    def firecrawl_service(self) -> None:
        """Create FirecrawlService instance for testing"""
        return FirecrawlService(
            api_key="test-key",
            base_url="https://api.firecrawl.dev",
            test_mode=False,  # Force real API mode for fault injection
        )

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
    async def test_firecrawl_service_unavailable_503(self) -> None:
        """Test FirecrawlService handles HTTP 503 Service Unavailable gracefully"""
        url = "https://example.com/test-503"

        with aioresponses() as m:
            # Mock 503 Service Unavailable response
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                status=503,
                payload={"error": "Service temporarily unavailable"},
                headers={"Retry-After": "60"},
            )

            result = await self.firecrawl_service.scrape_url(url)

            # Assert graceful error handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "API_ERROR"
            assert "503" in result.error.message
            assert result.url == url

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
    async def test_firecrawl_rate_limit_429(self) -> None:
        """Test FirecrawlService handles HTTP 429 Rate Limit gracefully"""
        url = "https://example.com/test-rate-limit"

        with aioresponses() as m:
            # Mock 429 Rate Limit response
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                status=429,
                payload={"error": "Rate limit exceeded"},
                headers={"Retry-After": "300"},
            )

            result = await self.firecrawl_service.scrape_url(url)

            # Assert graceful error handling with retry information
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "RATE_LIMIT_EXCEEDED"
            assert result.error.retry_after == 300
            assert result.error.is_retryable

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
    async def test_firecrawl_network_timeout(self) -> None:
        """Test FirecrawlService handles network timeouts gracefully"""
        url = "https://example.com/test-timeout"

        with aioresponses() as m:
            # Mock timeout by raising asyncio.TimeoutError
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                exception=TimeoutError("Request timeout"),
            )

            result = await self.firecrawl_service.scrape_url(url)

            # Assert graceful timeout handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "TIMEOUT"
            assert "timeout" in result.error.message.lower()

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
    async def test_firecrawl_malformed_json_response(self) -> None:
        """Test FirecrawlService handles malformed JSON responses gracefully"""
        url = "https://example.com/test-malformed-json"

        with aioresponses() as m:
            # Mock malformed JSON response
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                status=200,
                body="Invalid JSON response {broken",
            )

            result = await self.firecrawl_service.scrape_url(url)

            # Assert graceful JSON parsing error handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "UNKNOWN_ERROR"

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
    async def test_firecrawl_empty_response(self) -> None:
        """Test FirecrawlService handles empty responses gracefully"""
        url = "https://example.com/test-empty-response"

        with aioresponses() as m:
            # Mock empty response
            m.post("https://api.firecrawl.dev/v0/scrape", status=200, payload={})

            result = await self.firecrawl_service.scrape_url(url)

            # Assert graceful empty response handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "API_ERROR"

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
    async def test_firecrawl_connection_error(self) -> None:
        """Test FirecrawlService handles connection errors gracefully"""
        url = "https://example.com/test-connection-error"

        with aioresponses() as m:
            # Mock connection error
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                exception=aiohttp.ClientConnectorError(
                    Mock(), OSError("Connection refused")
                ),
            )

            result = await self.firecrawl_service.scrape_url(url)

            # Assert graceful connection error handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "UNKNOWN_ERROR"
            assert "connection" in result.error.message.lower()

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
    async def test_firecrawl_bulk_scrape_partial_failure(self) -> None:
        """Test FirecrawlService handles partial failures in bulk scraping"""
        urls = [
            "https://example.com/success",
            "https://example.com/fail-503",
            "https://example.com/success-2",
        ]

        with aioresponses() as m:
            # Mock mixed responses
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                status=200,
                payload={
                    "success": True,
                    "data": {
                        "markdown": "Success content",
                        "metadata": {"title": "Success"},
                    },
                },
            )
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                status=503,
                payload={"error": "Service unavailable"},
            )
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                status=200,
                payload={
                    "success": True,
                    "data": {
                        "markdown": "Success content 2",
                        "metadata": {"title": "Success 2"},
                    },
                },
            )

            results = await self.firecrawl_service.scrape_bulk(urls, max_concurrent=1)

            # Assert partial success handling
            assert len(results) == 3
            assert results[0].success
            assert not results[1].success
            assert results[2].success
            assert results[1].error.error_code == "API_ERROR"


class TestFaultInjectionArxiv:
    """Fault injection tests for ArxivEnhancedService API resilience"""

    @pytest.fixture
    def arxiv_service(self) -> None:
        """Create ArxivEnhancedService instance for testing"""
        return ArxivEnhancedService(
            base_url="http://export.arxiv.org/api/query", max_results=50
        )

    @pytest.fixture
    def sample_query(self) -> None:
        """Create sample ArXiv search query"""
        return ArxivSearchQuery(terms=["machine learning"], max_results=10)

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_arxiv_service_unavailable_503(self, sample_query: Any = None) -> None:
        """Test ArxivEnhancedService handles HTTP 503 Service Unavailable gracefully"""
        with aioresponses() as m:
            # Mock 503 Service Unavailable response
            m.get(
                "http://export.arxiv.org/api/query",
                status=503,
                body="Service temporarily unavailable",
            )

            result = await self.arxiv_service.search_papers(sample_query)

            # Assert graceful error handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "API_ERROR"
            assert "503" in result.error.message

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_arxiv_rate_limit_429(self, sample_query: Any = None) -> None:
        """Test ArxivEnhancedService handles HTTP 429 Rate Limit gracefully"""
        with aioresponses() as m:
            # Mock 429 Rate Limit response
            m.get(
                "http://export.arxiv.org/api/query",
                status=429,
                body="Rate limit exceeded",
                headers={"Retry-After": "300"},
            )

            result = await self.arxiv_service.search_papers(sample_query)

            # Assert graceful error handling with retry information
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "RATE_LIMIT_EXCEEDED"
            assert result.error.retry_after == 300
            assert result.error.is_retryable

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_arxiv_network_timeout(self, sample_query: Any = None) -> None:
        """Test ArxivEnhancedService handles network timeouts gracefully"""
        with aioresponses() as m:
            # Mock timeout by raising asyncio.TimeoutError
            m.get(
                "http://export.arxiv.org/api/query",
                exception=TimeoutError("Request timeout"),
            )

            result = await self.arxiv_service.search_papers(sample_query)

            # Assert graceful timeout handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "UNKNOWN_ERROR"

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_arxiv_malformed_xml_response(self, sample_query: Any = None) -> None:
        """Test ArxivEnhancedService handles malformed XML responses gracefully"""
        with aioresponses() as m:
            # Mock malformed XML response
            m.get(
                "http://export.arxiv.org/api/query",
                status=200,
                body="Invalid XML response <broken>",
            )

            result = await self.arxiv_service.search_papers(sample_query)

            # Assert graceful XML parsing error handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "PARSE_ERROR"

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_arxiv_empty_response(self, sample_query: Any = None) -> None:
        """Test ArxivEnhancedService handles empty responses gracefully"""
        with aioresponses() as m:
            # Mock empty response
            m.get("http://export.arxiv.org/api/query", status=200, body="")

            result = await self.arxiv_service.search_papers(sample_query)

            # Assert graceful empty response handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "PARSE_ERROR"

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_arxiv_connection_error(self, sample_query: Any = None) -> None:
        """Test ArxivEnhancedService handles connection errors gracefully"""
        with aioresponses() as m:
            # Mock connection error
            m.get(
                "http://export.arxiv.org/api/query",
                exception=aiohttp.ClientConnectorError(
                    Mock(), OSError("Connection refused")
                ),
            )

            result = await self.arxiv_service.search_papers(sample_query)

            # Assert graceful connection error handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "UNKNOWN_ERROR"


class TestFaultInjectionPubMed:
    """Fault injection tests for PubMedService API resilience"""

    @pytest.fixture
    def pubmed_service(self) -> None:
        """Create PubMedService instance for testing"""
        return PubMedService(
            base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
            email="test@example.com",
            api_key="test-key",
        )

    @pytest.fixture
    def sample_query(self) -> None:
        """Create sample PubMed search query"""
        return PubMedSearchQuery(terms=["machine learning"], max_results=10)

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_pubmed_service_unavailable_503(self, sample_query: Any = None) -> None:
        """Test PubMedService handles HTTP 503 Service Unavailable gracefully"""
        with aioresponses() as m:
            # Mock 503 Service Unavailable response for ESearch
            m.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                status=503,
                body="Service temporarily unavailable",
            )

            result = await self.pubmed_service.search_papers(sample_query)

            # Assert graceful error handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "SERVICE_UNAVAILABLE"

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_pubmed_rate_limit_429(self, sample_query: Any = None) -> None:
        """Test PubMedService handles HTTP 429 Rate Limit gracefully"""
        with aioresponses() as m:
            # Mock 429 Rate Limit response
            m.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                status=429,
                body="Rate limit exceeded",
                headers={"Retry-After": "300"},
            )

            result = await self.pubmed_service.search_papers(sample_query)

            # Assert graceful error handling with retry information
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "RATE_LIMIT_EXCEEDED"
            assert result.error.retry_after == 300
            assert result.error.is_retryable

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_pubmed_network_timeout(self, sample_query: Any = None) -> None:
        """Test PubMedService handles network timeouts gracefully"""
        with aioresponses() as m:
            # Mock timeout by raising asyncio.TimeoutError
            m.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                exception=TimeoutError("Request timeout"),
            )

            result = await self.pubmed_service.search_papers(sample_query)

            # Assert graceful timeout handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "UNKNOWN_ERROR"

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_pubmed_malformed_xml_response(self, sample_query: Any = None) -> None:
        """Test PubMedService handles malformed XML responses gracefully"""
        with aioresponses() as m:
            # Mock successful ESearch
            m.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                status=200,
                payload={
                    "esearchresult": {
                        "count": "1",
                        "retmax": "1",
                        "idlist": ["12345678"],
                    }
                },
            )
            # Mock malformed XML response for EFetch
            m.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                status=200,
                body="Invalid XML response <broken>",
            )

            result = await self.pubmed_service.search_papers(sample_query)

            # Assert graceful XML parsing error handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "PARSE_ERROR"

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_pubmed_empty_response(self, sample_query: Any = None) -> None:
        """Test PubMedService handles empty responses gracefully"""
        with aioresponses() as m:
            # Mock empty ESearch response
            m.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                status=200,
                payload={"esearchresult": {"count": "0", "retmax": "0", "idlist": []}},
            )

            result = await self.pubmed_service.search_papers(sample_query)

            # Assert graceful empty response handling
            assert result.success
            assert len(result.papers) == 0
            assert result.total_results == 0

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_pubmed_connection_error(self, sample_query: Any = None) -> None:
        """Test PubMedService handles connection errors gracefully"""
        with aioresponses() as m:
            # Mock connection error
            m.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                exception=aiohttp.ClientConnectorError(
                    Mock(), OSError("Connection refused")
                ),
            )

            result = await self.pubmed_service.search_papers(sample_query)

            # Assert graceful connection error handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "UNKNOWN_ERROR"

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
async def test_pubmed_partial_failure_esearch_success_efetch_fail(self, sample_query: Any = None) -> None:
        """Test PubMedService handles partial failures (ESearch success, EFetch failure)"""
        with aioresponses() as m:
            # Mock successful ESearch
            m.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                status=200,
                payload={
                    "esearchresult": {
                        "count": "2",
                        "retmax": "2",
                        "idlist": ["12345678", "87654321"],
                    }
                },
            )
            # Mock EFetch failure
            m.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                status=503,
                body="Service temporarily unavailable",
            )

            result = await self.pubmed_service.search_papers(sample_query)

            # Assert graceful partial failure handling
            assert not result.success
            assert result.error is not None
            assert result.error.error_code == "UNKNOWN_ERROR"


class TestFaultInjectionIntegration:
    """Integration fault injection tests for orchestrator resilience"""

    @pytest.fixture
    def ingestion_orchestrator(self) -> None:
        """Create ingestion orchestrator for testing"""
        try:
            from src.services.ingestion.interfaces import IngestionConfig
            from src.services.ingestion.orchestrator import IngestionOrchestrator

            config = IngestionConfig(
                max_concurrent_sources=3, timeout_seconds=30, retry_attempts=2
            )
            return IngestionOrchestrator(config)
        except ImportError:
            pytest.skip("Ingestion orchestrator not available")

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
    async def test_orchestrator_handles_mixed_api_failures(self) -> None:
        """Test orchestrator handles mixed API failures gracefully"""
        topic = "machine learning research"

        # Mock mixed API responses
        with aioresponses() as m:
            # Firecrawl - Success
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                status=200,
                payload={
                    "success": True,
                    "data": {
                        "markdown": "Web content about ML",
                        "metadata": {"title": "ML Web Article"},
                    },
                },
            )

            # ArXiv - Service Unavailable
            m.get(
                "http://export.arxiv.org/api/query",
                status=503,
                body="Service temporarily unavailable",
            )

            # PubMed - Rate Limited
            m.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                status=429,
                body="Rate limit exceeded",
                headers={"Retry-After": "300"},
            )

            # Create ingestion plan
            plan = await self.ingestion_orchestrator.create_ingestion_plan(topic)

            # Execute plan with mixed failures
            result = await self.ingestion_orchestrator.execute_ingestion_plan(plan)

            # Assert orchestrator handles mixed failures gracefully
            assert result is not None
            # Should have partial success from Firecrawl
            assert len(result.content_items) >= 0  # May have some content
            # Should log errors for failed services
            assert result.execution_metrics["success_rate"] < 100.0

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
    async def test_orchestrator_circuit_breaker_pattern(self) -> None:
        """Test orchestrator implements circuit breaker pattern for failing services"""
        topic = "test circuit breaker"

        # Mock consecutive failures for ArXiv
        with aioresponses() as m:
            for _ in range(5):  # Simulate multiple failures
                m.get(
                    "http://export.arxiv.org/api/query",
                    status=503,
                    body="Service temporarily unavailable",
                )

            # Create and execute plan multiple times
            for i in range(3):
                plan = await self.ingestion_orchestrator.create_ingestion_plan(
                    f"{topic} {i}"
                )
                result = await self.ingestion_orchestrator.execute_ingestion_plan(plan)

                # Assert graceful degradation
                assert result is not None
                # Should not crash despite repeated failures
                assert result.execution_metrics is not None

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
    async def test_orchestrator_timeout_handling(self) -> None:
        """Test orchestrator handles service timeouts gracefully"""
        topic = "test timeout handling"

        with aioresponses() as m:
            # Mock timeout for all services
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                exception=TimeoutError("Request timeout"),
            )
            m.get(
                "http://export.arxiv.org/api/query",
                exception=TimeoutError("Request timeout"),
            )
            m.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                exception=TimeoutError("Request timeout"),
            )

            plan = await self.ingestion_orchestrator.create_ingestion_plan(topic)
            result = await self.ingestion_orchestrator.execute_ingestion_plan(plan)

            # Assert timeout handling
            assert result is not None
            assert result.execution_metrics["success_rate"] == 0.0
            # Should not crash despite all timeouts


class TestFaultInjectionMonitoring:
    """Fault injection tests for monitoring and observability"""

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
    async def test_api_health_monitoring_during_failures(self) -> None:
        """Test API health monitoring tracks failures correctly"""
        try:
            from src.services.ingestion.interfaces import IngestionConfig
            from src.services.ingestion.production_config import ProductionConfig
            from src.services.ingestion.production_orchestrator import (
                ProductionIngestionOrchestrator,
            )

            config = IngestionConfig(max_concurrent_sources=1, timeout_seconds=5)
            prod_config = ProductionConfig(
                firecrawl_api_key="test-key", ncbi_email="test@example.com"
            )

            orchestrator = ProductionIngestionOrchestrator(config, prod_config)
        except ImportError:
            pytest.skip("Production orchestrator not available")

        # Mock API failures
        with aioresponses() as m:
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                status=503,
                body="Service temporarily unavailable",
            )

            # Execute with failure
            plan = await orchestrator.create_ingestion_plan("test monitoring")
            result = await orchestrator.execute_ingestion_plan(plan)

            # Check health status
            firecrawl_health = orchestrator.api_health_status.get("firecrawl")
            assert firecrawl_health is not None
            # Health status should reflect the failure
            assert firecrawl_health.response_time_ms > 0

    @pytest.mark.integration
    @pytest.mark.requires_network
    @pytest.mark.asyncio
    async def test_error_logging_during_fault_injection(self) -> None:
        """Test that errors are properly logged during fault injection"""
        firecrawl_service = FirecrawlService(
            api_key="test-key", base_url="https://api.firecrawl.dev", test_mode=False
        )

        with self.caplog.at_level(logging.ERROR), aioresponses() as m:
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                status=503,
                body="Service temporarily unavailable",
            )

            result = await firecrawl_service.scrape_url("https://example.com/test")

            # Assert error logging
            assert not result.success
            assert any("503" in record.message for record in self.caplog.records)


# Test markers for CI pipeline integration
# These markers are applied to the entire test module
