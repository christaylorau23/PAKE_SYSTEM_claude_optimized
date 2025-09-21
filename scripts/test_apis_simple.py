#!/usr/bin/env python3
"""
Simple API Testing Script - Windows Compatible
Tests Phase 2B production APIs without Unicode issues
"""

import asyncio
import os

import aiohttp
from dotenv import load_dotenv


def print_status(status, message):
    """Print status without Unicode characters"""
    if status == "SUCCESS":
        print(f"[OK] {message}")
    elif status == "ERROR":
        print(f"[ERROR] {message}")
    elif status == "WARNING":
        print(f"[WARN] {message}")
    else:
        print(f"[INFO] {message}")


async def test_firecrawl_api(api_key):
    """Test Firecrawl API"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            test_data = {"url": "https://httpbin.org/html", "formats": ["markdown"]}

            async with session.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers=headers,
                json=test_data,
                timeout=30,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        return True, "Firecrawl API working correctly"
                    return (
                        False,
                        f"API returned error: {result.get('error', 'Unknown')}",
                    )
                text = await response.text()
                return False, f"HTTP {response.status}: {text[:100]}"

    except Exception as e:
        return False, f"Connection error: {str(e)}"


async def test_arxiv_api():
    """Test ArXiv API"""
    try:
        async with aiohttp.ClientSession() as session:
            params = {"search_query": "cat:cs.AI", "max_results": "1"}

            async with session.get(
                "http://export.arxiv.org/api/query",
                params=params,
                timeout=30,
            ) as response:
                if response.status == 200:
                    content = await response.text()
                    if "<entry>" in content:
                        return True, "ArXiv API working correctly"
                    return False, "No results from ArXiv"
                return False, f"HTTP {response.status}"

    except Exception as e:
        return False, f"Connection error: {str(e)}"


async def main():
    print("PAKE+ Production API Test - Phase 2B")
    print("=" * 50)

    # Load environment
    load_dotenv()

    # Test Firecrawl
    print("Testing Firecrawl API...")
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")

    if firecrawl_key and firecrawl_key.startswith("fc-"):
        success, message = await test_firecrawl_api(firecrawl_key)
        print_status("SUCCESS" if success else "ERROR", f"Firecrawl: {message}")
    else:
        print_status("WARNING", "Firecrawl API key not configured or invalid")

    # Test ArXiv
    print("Testing ArXiv API...")
    success, message = await test_arxiv_api()
    print_status("SUCCESS" if success else "ERROR", f"ArXiv: {message}")

    # Check PubMed email
    pubmed_email = os.getenv("PUBMED_EMAIL")
    if pubmed_email and "@" in pubmed_email and pubmed_email != "your_email@domain.com":
        print_status("SUCCESS", f"PubMed email configured: {pubmed_email}")
    else:
        print_status("WARNING", "PubMed email not configured")

    print("\n" + "=" * 50)
    print("Quick API Test Complete!")
    print(
        "Ready to run full pipeline test with: python scripts/run_omni_source_pipeline.py",
    )


if __name__ == "__main__":
    asyncio.run(main())
