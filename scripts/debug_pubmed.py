#!/usr/bin/env python3
"""
PAKE System - Simple PubMed Fault Injection Test
Debug script to understand PubMed service behavior
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


async def test_pubmed_debug(self) -> None:
    """Debug PubMed service behavior"""
    try:
        from aioresponses import aioresponses

        from services.ingestion.pubmed_service import PubMedSearchQuery, PubMedService

        print("🧪 Debugging PubMedService behavior...")

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

            print("   Making request to PubMed service...")
            result = await service.search_papers(query)

            print(f"   Result success: {result.success}")
            if result.error:
                print(f"   Error code: {result.error.error_code}")
                print(f"   Error message: {result.error.message}")
            else:
                print("   No error information")
                print(f"   Papers found: {len(result.papers)}")
                print(f"   Total results: {result.total_results}")

            # Test what happens when we call _esearch directly
            print("\n   Testing _esearch directly...")
            try:
                esearch_result = await service._esearch("machine learning", 10, 0)
                print(f"   ESearch result: {esearch_result}")
            except Exception as e:
                print(f"   ESearch exception: {e}")

            return result.success is False and result.error is not None

    except Exception as e:
        print(f"❌ PubMed debug test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_pubmed_debug())
    print(f"\n📊 Debug result: {'✅ Success' if success else '❌ Failed'}")
    sys.exit(0 if success else 1)
