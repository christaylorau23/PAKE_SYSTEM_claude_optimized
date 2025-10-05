#!/usr/bin/env python3
"""
PAKE System - Fault Injection Test Validation Script
Simple script to validate fault injection tests work correctly
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


async def test_firecrawl_fault_injection(self) -> None:
    """Test FirecrawlService fault injection"""
    try:
        from aioresponses import aioresponses

        from services.ingestion.firecrawl_service import FirecrawlService

        print("🧪 Testing FirecrawlService fault injection...")

        service = FirecrawlService(
            api_key="test-key", base_url="https://api.firecrawl.dev", test_mode=False
        )

        with aioresponses() as m:
            # Mock 503 Service Unavailable response
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                status=503,
                payload={"error": "Service temporarily unavailable"},
                headers={"Retry-After": "60"},
            )

            result = await service.scrape_url("https://example.com/test-503")

            # Validate graceful error handling
            assert not result.success, "Should handle 503 error gracefully"
            assert result.error is not None, "Should have error information"
            assert (
                result.error.error_code == "API_ERROR"
            ), "Should have correct error code"
            assert (
                "503" in result.error.message
            ), "Should include status code in error message"

            print("✅ FirecrawlService handles 503 errors gracefully")
            return True

    except Exception as e:
        print(f"❌ FirecrawlService fault injection test failed: {e}")
        return False


async def test_arxiv_fault_injection(self) -> None:
    """Test ArxivEnhancedService fault injection"""
    try:
        from aioresponses import aioresponses

        from services.ingestion.arxiv_enhanced_service import (
            ArxivEnhancedService,
            ArxivSearchQuery,
        )

        print("🧪 Testing ArxivEnhancedService fault injection...")

        service = ArxivEnhancedService(
            base_url="http://export.arxiv.org/api/query", max_results=50
        )

        query = ArxivSearchQuery(terms=["machine learning"], max_results=10)

        with aioresponses() as m:
            # Mock 503 Service Unavailable response
            m.get(
                "http://export.arxiv.org/api/query",
                status=503,
                body="Service temporarily unavailable",
            )

            result = await service.search_papers(query)

            # Debug information
            print(f"   Result success: {result.success}")
            if result.error:
                print(f"   Error code: {result.error.error_code}")
                print(f"   Error message: {result.error.message}")
            else:
                print("   No error information")

            # Validate graceful error handling
            assert (
                not result.success
            ), f"Should handle 503 error gracefully, but got success={result.success}"
            assert result.error is not None, "Should have error information"
            assert result.error.error_code in [
                "API_ERROR",
                "SERVICE_UNAVAILABLE",
            ], f"Should have correct error code, got {result.error.error_code}"

            print("✅ ArxivEnhancedService handles 503 errors gracefully")
            return True

    except Exception as e:
        print(f"❌ ArxivEnhancedService fault injection test failed: {e}")
        return False


async def test_pubmed_fault_injection(self) -> None:
    """Test PubMedService fault injection"""
    try:
        from aioresponses import aioresponses

        from services.ingestion.pubmed_service import PubMedSearchQuery, PubMedService

        print("🧪 Testing PubMedService fault injection...")

        service = PubMedService(
            base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
            email="test@example.com",
            api_key="test-key",
        )

        query = PubMedSearchQuery(terms=["machine learning"], max_results=10)

        with aioresponses() as m:
            # Mock 503 Service Unavailable response for ESearch
            m.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                status=503,
                body="Service temporarily unavailable",
            )

            result = await service.search_papers(query)

            # Debug information
            print(f"   Result success: {result.success}")
            if result.error:
                print(f"   Error code: {result.error.error_code}")
                print(f"   Error message: {result.error.message}")
            else:
                print("   No error information")
                print(f"   Papers found: {len(result.papers)}")
                print(f"   Total results: {result.total_results}")

            # Validate graceful error handling
            assert (
                not result.success
            ), f"Should handle 503 error gracefully, but got success={result.success}"
            assert result.error is not None, "Should have error information"
            assert result.error.error_code in [
                "API_ERROR",
                "SERVICE_UNAVAILABLE",
            ], f"Should have correct error code, got {result.error.error_code}"

            print("✅ PubMedService handles 503 errors gracefully")
            return True

    except Exception as e:
        print(f"❌ PubMedService fault injection test failed: {e}")
        return False


async def test_rate_limit_handling(self) -> None:
    """Test rate limit handling across all services"""
    try:
        from aioresponses import aioresponses

        from services.ingestion.firecrawl_service import FirecrawlService

        print("🧪 Testing rate limit handling...")

        service = FirecrawlService(
            api_key="test-key", base_url="https://api.firecrawl.dev", test_mode=False
        )

        with aioresponses() as m:
            # Mock 429 Rate Limit response
            m.post(
                "https://api.firecrawl.dev/v0/scrape",
                status=429,
                payload={"error": "Rate limit exceeded"},
                headers={"Retry-After": "300"},
            )

            result = await service.scrape_url("https://example.com/test-rate-limit")

            # Validate rate limit handling
            assert not result.success, "Should handle rate limit gracefully"
            assert result.error is not None, "Should have error information"
            assert (
                result.error.error_code == "RATE_LIMIT_EXCEEDED"
            ), "Should have correct error code"
            assert result.error.retry_after == 300, "Should extract retry-after header"
            assert result.error.is_retryable, "Should indicate error is retryable"

            print("✅ Rate limit handling works correctly")
            return True

    except Exception as e:
        print(f"❌ Rate limit handling test failed: {e}")
        return False


async def main(self) -> None:
    """Run all fault injection tests"""
    print("🚀 Starting Fault Injection Test Validation")
    print("=" * 50)

    tests = [
        test_firecrawl_fault_injection,
        test_arxiv_fault_injection,
        test_pubmed_fault_injection,
        test_rate_limit_handling,
    ]

    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
        print()

    # Summary
    passed = sum(results)
    total = len(results)

    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All fault injection tests passed!")
        print("🎯 System demonstrates resilience to external API failures")
        return True
    print("❌ Some fault injection tests failed")
    print("🔧 System needs improvement in error handling")
    return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
