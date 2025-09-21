#!/usr/bin/env python3
"""
PAKE+ Production API Setup & Validation Script
Validates and configures real API integrations for Phase 2B deployment
"""

import asyncio
import os
import sys
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

# Colors for terminal output


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_status(status: str, message: str):
    """Print colored status message"""
    if status == "SUCCESS":
        print(f"{Colors.GREEN}✅ {message}{Colors.END}")
    elif status == "ERROR":
        print(f"{Colors.RED}❌ {message}{Colors.END}")
    elif status == "WARNING":
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")
    elif status == "INFO":
        print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")
    elif status == "STEP":
        print(f"{Colors.PURPLE}🔄 {message}{Colors.END}")


def print_header(title: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}\n")


async def validate_firecrawl_api(api_key: str, base_url: str) -> tuple[bool, str]:
    """Validate Firecrawl API credentials"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            # Test with a simple scraping request
            test_data = {"url": "https://httpbin.org/html", "formats": ["markdown"]}

            async with session.post(
                f"{base_url}/v1/scrape",
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
                        f"API returned success=false: {
                            result.get('error', 'Unknown error')
                        }",
                    )
                error_text = await response.text()
                return False, f"HTTP {response.status}: {error_text[:200]}"

    except Exception as e:
        return False, f"Connection error: {str(e)}"


async def validate_pubmed_api(
    email: str,
    api_key: str | None = None,
) -> tuple[bool, str]:
    """Validate PubMed E-utilities access"""
    try:
        async with aiohttp.ClientSession() as session:
            # Test ESearch endpoint
            params = {
                "db": "pubmed",
                "term": "covid-19[Title]",
                "retmax": "1",
                "retmode": "json",
                "email": email,
            }

            if api_key:
                params["api_key"] = api_key

            async with session.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params=params,
                timeout=30,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if (
                        "esearchresult" in result
                        and result["esearchresult"].get("count", "0") != "0"
                    ):
                        return True, "PubMed API working correctly"
                    return (
                        False,
                        "No search results returned (possible rate limiting)",
                    )
                error_text = await response.text()
                return False, f"HTTP {response.status}: {error_text[:200]}"

    except Exception as e:
        return False, f"Connection error: {str(e)}"


async def validate_arxiv_api() -> tuple[bool, str]:
    """Validate ArXiv API access"""
    try:
        async with aiohttp.ClientSession() as session:
            # Test ArXiv API
            params = {"search_query": "cat:cs.AI", "max_results": "1"}

            async with session.get(
                "http://export.arxiv.org/api/query",
                params=params,
                timeout=30,
            ) as response:
                if response.status == 200:
                    content = await response.text()
                    if "<entry>" in content and "<title>" in content:
                        return True, "ArXiv API working correctly"
                    return False, "Invalid response format from ArXiv"
                error_text = await response.text()
                return False, f"HTTP {response.status}: {error_text[:200]}"

    except Exception as e:
        return False, f"Connection error: {str(e)}"


def check_environment_setup() -> dict[str, bool]:
    """Check if environment variables are properly configured"""
    required_vars = {
        "FIRECRAWL_API_KEY": False,
        "PUBMED_EMAIL": False,
        "VAULT_PATH": False,
        "OBSIDIAN_BRIDGE_PORT": False,
    }

    optional_vars = {
        "PUBMED_API_KEY": False,
        "GMAIL_CLIENT_ID": False,
        "TWITTER_BEARER_TOKEN": False,
        "REDIS_URL": False,
        "OPENAI_API_KEY": False,
    }

    all_vars = {**required_vars, **optional_vars}

    for var in all_vars:
        value = os.getenv(var)
        if value and value != f"your_{var.lower()}_here" and value.strip():
            all_vars[var] = True

    return {"required": required_vars, "optional": optional_vars, "all": all_vars}


async def test_production_pipeline():
    """Test the full production pipeline with real APIs"""
    print_step("Testing production omni-source pipeline...")

    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    try:
        from services.ingestion.orchestrator import (
            IngestionConfig,
            IngestionOrchestrator,
        )

        # Create production config
        config = IngestionConfig(
            max_concurrent_sources=5,
            timeout_per_source=120,
            quality_threshold=0.8,
            enable_cognitive_processing=True,
            deduplication_enabled=True,
            caching_enabled=True,
        )

        orchestrator = IngestionOrchestrator(config=config)

        # Test with a real research topic
        plan = await orchestrator.create_ingestion_plan(
            "machine learning applications in healthcare 2024",
            {
                "domain": "healthcare",
                "urgency": "high",
                "quality_threshold": 0.8,
                "enable_query_optimization": True,
            },
        )

        print_status("INFO", f"Created plan with {len(plan.sources)} sources")

        # Execute the plan
        result = await orchestrator.execute_ingestion_plan(plan)

        if result.success:
            print_status(
                "SUCCESS",
                f"Pipeline test completed: {len(result.content_items)} items collected",
            )
            return True
        print_status("ERROR", "Pipeline test failed")
        return False

    except Exception as e:
        print_status("ERROR", f"Pipeline test error: {str(e)}")
        return False


def generate_production_summary(env_status: dict, api_results: dict) -> str:
    """Generate a summary report for production readiness"""

    summary = f"""
{Colors.BOLD}PAKE+ SYSTEM - PRODUCTION READINESS REPORT{Colors.END}
Generated: {os.popen("date").read().strip()}

{Colors.CYAN}ENVIRONMENT CONFIGURATION:{Colors.END}
"""

    # Required variables status
    required_count = sum(1 for v in env_status["required"].values() if v)
    total_required = len(env_status["required"])
    summary += f"Required Variables: {required_count}/{total_required} configured\n"

    for var, status in env_status["required"].items():
        status_icon = "✅" if status else "❌"
        summary += f"  {status_icon} {var}\n"

    # Optional variables status
    optional_count = sum(1 for v in env_status["optional"].values() if v)
    total_optional = len(env_status["optional"])
    summary += f"\nOptional Variables: {optional_count}/{total_optional} configured\n"

    for var, status in env_status["optional"].items():
        status_icon = "✅" if status else "⭕"
        summary += f"  {status_icon} {var}\n"

    summary += f"\n{Colors.CYAN}API VALIDATION RESULTS:{Colors.END}\n"

    for api, (status, message) in api_results.items():
        status_icon = "✅" if status else "❌"
        summary += f"  {status_icon} {api.upper()}: {message}\n"

    # Calculate overall readiness
    required_ready = required_count == total_required
    apis_working = sum(1 for status, _ in api_results.values() if status)
    total_apis = len(api_results)

    summary += f"\n{Colors.CYAN}OVERALL ASSESSMENT:{Colors.END}\n"

    if required_ready and apis_working >= 2:
        summary += f"{Colors.GREEN}🚀 PRODUCTION READY{Colors.END}\n"
        summary += "   • All required configurations set\n"
        summary += f"   • {apis_working}/{total_apis} APIs operational\n"
        summary += "   • System ready for Phase 2B deployment\n"
    elif required_ready:
        summary += f"{Colors.YELLOW}⚠️  PARTIALLY READY{Colors.END}\n"
        summary += "   • Required configurations set\n"
        summary += f"   • {apis_working}/{total_apis} APIs operational\n"
        summary += "   • Consider getting additional API credentials\n"
    else:
        summary += f"{Colors.RED}❌ NOT READY{Colors.END}\n"
        summary += (
            f"   • {total_required - required_count} required configurations missing\n"
        )
        summary += "   • Complete .env setup before deployment\n"

    summary += f"\n{Colors.CYAN}NEXT STEPS:{Colors.END}\n"

    if not required_ready:
        summary += "1. Complete .env configuration (copy from .env.template)\n"
        summary += "2. Get required API credentials (see instructions below)\n"
        summary += "3. Re-run this script to validate\n"
    else:
        summary += "1. Deploy advanced services (email, social media, RSS)\n"
        summary += "2. Set up production monitoring and analytics\n"
        summary += "3. Configure authentication and security features\n"

    return summary


async def main():
    """Main setup and validation process"""

    print_header("PAKE+ PRODUCTION API SETUP & VALIDATION")

    # Load environment variables
    env_file = Path(".env")
    env_template = Path(".env.template")

    if not env_file.exists():
        if env_template.exists():
            print_status(
                "WARNING",
                ".env file not found. Please copy .env.template to .env and configure your credentials",
            )
            print_status("INFO", "Run: copy .env.template .env")
            return
        print_status(
            "ERROR",
            "No .env.template found. Something went wrong with the setup.",
        )
        return

    load_dotenv()

    print_step("Checking environment configuration...")
    env_status = check_environment_setup()

    required_missing = [k for k, v in env_status["required"].items() if not v]
    if required_missing:
        print_status(
            "ERROR",
            f"Missing required environment variables: {', '.join(required_missing)}",
        )
        print_status(
            "INFO",
            "Please configure your .env file with the required API credentials",
        )
        return

    print_status("SUCCESS", "All required environment variables configured")

    # Test API connections
    print_header("VALIDATING API CONNECTIONS")

    api_results = {}

    # Test Firecrawl
    print_step("Testing Firecrawl API...")
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
    firecrawl_url = os.getenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev")

    if firecrawl_key and firecrawl_key != "your_firecrawl_api_key_here":
        success, message = await validate_firecrawl_api(firecrawl_key, firecrawl_url)
        api_results["firecrawl"] = (success, message)
        print_status("SUCCESS" if success else "ERROR", f"Firecrawl: {message}")
    else:
        api_results["firecrawl"] = (False, "API key not configured")
        print_status("WARNING", "Firecrawl API key not configured")

    # Test PubMed
    print_step("Testing PubMed API...")
    pubmed_email = os.getenv("PUBMED_EMAIL")
    pubmed_key = os.getenv("PUBMED_API_KEY")

    if pubmed_email and pubmed_email != "your_email@domain.com":
        success, message = await validate_pubmed_api(pubmed_email, pubmed_key)
        api_results["pubmed"] = (success, message)
        print_status("SUCCESS" if success else "ERROR", f"PubMed: {message}")
    else:
        api_results["pubmed"] = (False, "Email not configured")
        print_status("WARNING", "PubMed email not configured")

    # Test ArXiv (always available)
    print_step("Testing ArXiv API...")
    success, message = await validate_arxiv_api()
    api_results["arxiv"] = (success, message)
    print_status("SUCCESS" if success else "ERROR", f"ArXiv: {message}")

    # Test production pipeline
    print_header("TESTING PRODUCTION PIPELINE")
    pipeline_success = await test_production_pipeline()
    api_results["pipeline"] = (pipeline_success, "End-to-end pipeline test")

    # Generate and display summary
    print_header("PRODUCTION READINESS SUMMARY")
    summary = generate_production_summary(env_status, api_results)
    print(summary)

    # Save summary to file
    with open("production_readiness_report.txt", "w") as f:
        # Remove ANSI color codes for file
        import re

        clean_summary = re.sub(r"\033\[[0-9;]*m", "", summary)
        f.write(clean_summary)

    print_status("INFO", "Full report saved to: production_readiness_report.txt")


def print_step(message: str):
    print_status("STEP", message)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Setup interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Setup failed: {str(e)}{Colors.END}")
