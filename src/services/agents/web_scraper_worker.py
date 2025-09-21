#!/usr/bin/env python3
"""PAKE System - Web Scraper Worker Agent
Stateless worker for JavaScript-heavy web scraping using Firecrawl service.

Handles:
- URL scraping with JavaScript rendering
- Content extraction and structuring
- Error handling and retries
- Performance optimization
"""

import logging
from datetime import UTC, datetime
from typing import Any

from scripts.ingestion_pipeline import ContentItem

from ..ingestion.firecrawl_service import FirecrawlService, ScrapingOptions
from ..messaging.message_bus import MessageBus
from .base_worker import BaseWorkerAgent, WorkerCapabilityBuilder

# Configure logging
logger = logging.getLogger(__name__)


class WebScraperWorker(BaseWorkerAgent):
    """Stateless worker agent for web scraping operations.

    Processes web scraping tasks from the supervisor using the Firecrawl service
    for JavaScript-heavy content extraction.
    """

    def __init__(
        self,
        message_bus: MessageBus,
        firecrawl_api_key: str = "test-key",
        worker_id: str = None,
    ):
        """Initialize web scraper worker"""
        # Define worker capabilities
        capabilities = [
            WorkerCapabilityBuilder("web_scraping")
            .with_description(
                "Extract content from web pages with JavaScript rendering",
            )
            .with_input_types("url", "scraping_options")
            .with_output_types("content_item", "structured_content")
            .with_performance_metrics(
                average_scrape_time=3.5,
                success_rate=0.95,
                javascript_support=True,
            )
            .build(),
            WorkerCapabilityBuilder("javascript_rendering")
            .with_description("Render JavaScript-heavy SPAs and dynamic content")
            .with_input_types("url", "wait_time", "selectors")
            .with_output_types("rendered_html", "extracted_text")
            .with_performance_metrics(
                rendering_time=2.8,
                spa_support=True,
                dynamic_content_extraction=True,
            )
            .build(),
            WorkerCapabilityBuilder("content_structuring")
            .with_description("Structure scraped content into standardized format")
            .with_input_types("raw_html", "metadata")
            .with_output_types("content_item", "structured_metadata")
            .with_performance_metrics(processing_speed="high", metadata_extraction=True)
            .build(),
        ]

        super().__init__(
            worker_type="web_scraper",
            message_bus=message_bus,
            capabilities=capabilities,
            worker_id=worker_id,
        )

        # Initialize Firecrawl service
        self.firecrawl_service = FirecrawlService(api_key=firecrawl_api_key)

        # Web scraper specific configuration
        self.max_task_timeout = 120.0  # 2 minutes for web scraping
        self.default_wait_time = 3000  # 3 seconds for JavaScript rendering

        logger.info(f"WebScraperWorker {self.worker_id} initialized")

    async def process_task(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """Process web scraping task.

        Handles 'web_ingestion' tasks from the supervisor with source configurations.
        """
        try:
            # Extract task parameters
            source_data = task_data.get("source", {})
            plan_context = task_data.get("plan_context", {})

            # Parse source configuration
            query_params = source_data.get("query_parameters", {})
            urls = query_params.get("urls", [])
            scraping_opts = query_params.get("scraping_options", {})

            if not urls:
                return {
                    "success": False,
                    "error": "No URLs provided for scraping",
                    "result": None,
                }

            # Configure scraping options
            options = self._create_scraping_options(scraping_opts)

            # Process each URL
            content_items = []
            errors = []

            for url in urls:
                try:
                    # Scrape URL with Firecrawl service
                    result = await self.firecrawl_service.scrape_url(url, options)

                    if result.success:
                        # Convert to ContentItem
                        content_item = await self.firecrawl_service.to_content_item(
                            result,
                            f"web_scraper_{self.worker_id}",
                        )

                        # Enhance with context metadata
                        self._enhance_content_metadata(
                            content_item,
                            plan_context,
                            source_data,
                        )

                        content_items.append(content_item.__dict__)

                        logger.debug(f"Successfully scraped {url}")

                    else:
                        error_msg = f"Scraping failed for {url}: {result.error}"
                        errors.append(error_msg)
                        logger.warning(error_msg)

                except Exception as e:
                    error_msg = f"Error scraping {url}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # Determine success based on results
            success = len(content_items) > 0
            error_message = "; ".join(errors) if errors else None

            return {
                "success": success,
                "result": content_items,
                "error": error_message,
                "metrics": {
                    "urls_processed": len(urls),
                    "successful_scrapes": len(content_items),
                    "failed_scrapes": len(errors),
                    "total_content_length": sum(
                        len(item.get("content", "")) for item in content_items
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Web scraper task processing error: {e}")
            return {
                "success": False,
                "error": f"Task processing failed: {str(e)}",
                "result": None,
            }

    def _create_scraping_options(
        self,
        scraping_opts: dict[str, Any],
    ) -> ScrapingOptions:
        """Create ScrapingOptions from configuration"""
        return ScrapingOptions(
            wait_time=scraping_opts.get("wait_time", self.default_wait_time),
            extract_metadata=scraping_opts.get("extract_metadata", True),
            include_links=scraping_opts.get("include_links", True),
            include_headings=scraping_opts.get("include_headings", True),
            follow_redirects=scraping_opts.get("follow_redirects", True),
            user_agent=scraping_opts.get(
                "user_agent",
                f"PAKE-WebScraper/{self.worker_id}",
            ),
            timeout=min(
                scraping_opts.get("timeout", 60000),  # 60 seconds
                int(self.max_task_timeout * 1000),  # Convert to milliseconds
            ),
        )

    def _enhance_content_metadata(
        self,
        content_item: ContentItem,
        plan_context: dict[str, Any],
        source_data: dict[str, Any],
    ):
        """Enhance content item with additional metadata"""
        if not content_item.metadata:
            content_item.metadata = {}

        # Add worker information
        content_item.metadata.update(
            {
                "worker_id": self.worker_id,
                "worker_type": self.worker_type,
                "processing_timestamp": datetime.now(UTC).isoformat(),
                "scraping_method": "firecrawl_stateless",
                "javascript_rendered": True,
            },
        )

        # Add plan context
        if plan_context:
            content_item.metadata.update(
                {
                    "plan_id": plan_context.get("plan_id"),
                    "research_topic": plan_context.get("topic"),
                    "cognitive_processing_enabled": plan_context.get(
                        "cognitive_processing",
                        False,
                    ),
                },
            )

        # Add source information
        if source_data:
            content_item.metadata.update(
                {
                    "source_priority": source_data.get("priority"),
                    "source_timeout": source_data.get("timeout"),
                    "estimated_results": source_data.get("estimated_results"),
                },
            )

    async def _on_start(self):
        """Web scraper specific startup logic"""
        # Test Firecrawl service connection
        try:
            test_result = await self.firecrawl_service.scrape_url(
                "https://example.com",
                ScrapingOptions(timeout=10000),
            )

            if test_result.success:
                logger.info(
                    f"WebScraperWorker {self.worker_id} Firecrawl service test successful",
                )
            else:
                logger.warning(
                    f"WebScraperWorker {
                        self.worker_id
                    } Firecrawl service test warning: {test_result.error}",
                )

        except Exception as e:
            logger.error(
                f"WebScraperWorker {self.worker_id} Firecrawl service test failed: {e}",
            )

    async def _on_stop(self):
        """Web scraper specific cleanup logic"""
        # No specific cleanup needed for stateless worker
        logger.info(f"WebScraperWorker {self.worker_id} cleanup completed")

    async def get_health_status(self) -> dict[str, Any]:
        """Get web scraper specific health status"""
        base_health = await super().get_health_status()

        # Add web scraper specific health information
        web_scraper_health = {
            "firecrawl_service_status": "healthy",  # Could add actual service test
            "default_wait_time": self.default_wait_time,
            "max_task_timeout": self.max_task_timeout,
            "javascript_rendering_enabled": True,
        }

        # Test Firecrawl service health
        try:
            test_result = await self.firecrawl_service.scrape_url(
                "https://httpbin.org/status/200",
                ScrapingOptions(timeout=5000),
            )

            if not test_result.success:
                web_scraper_health["firecrawl_service_status"] = "degraded"
                web_scraper_health["firecrawl_service_error"] = test_result.error

        except Exception as e:
            web_scraper_health["firecrawl_service_status"] = "unhealthy"
            web_scraper_health["firecrawl_service_error"] = str(e)

        base_health.update(web_scraper_health)
        return base_health


# Factory function for creating web scraper workers
async def create_web_scraper_worker(
    message_bus: MessageBus,
    firecrawl_api_key: str = None,
    worker_id: str = None,
) -> WebScraperWorker:
    """Create and start a web scraper worker.

    Args:
        message_bus: Message bus for communication
        firecrawl_api_key: API key for Firecrawl service
        worker_id: Optional custom worker ID

    Returns:
        Started WebScraperWorker instance
    """
    # Use environment variable or default test key
    if firecrawl_api_key is None:
        import os

        firecrawl_api_key = os.getenv(
            "FIRECRAWL_API_KEY",
            "fc-test-key-development-only",
        )

    worker = WebScraperWorker(
        message_bus=message_bus,
        firecrawl_api_key=firecrawl_api_key,
        worker_id=worker_id,
    )

    await worker.start()
    return worker


# Task type handlers for different web scraping scenarios
class WebScrapingTaskTypes:
    """Web scraping task type definitions"""

    BASIC_SCRAPING = "web_scraping_basic"
    JAVASCRIPT_HEAVY = "web_scraping_javascript"
    SPA_CONTENT = "web_scraping_spa"
    STRUCTURED_DATA = "web_scraping_structured"
    BULK_URLS = "web_scraping_bulk"


def create_web_scraping_task_data(
    urls: list[str],
    task_type: str = WebScrapingTaskTypes.BASIC_SCRAPING,
    wait_time: int = 3000,
    extract_metadata: bool = True,
    **kwargs,
) -> dict[str, Any]:
    """Create task data for web scraping operations.

    Args:
        urls: List of URLs to scrape
        task_type: Type of web scraping task
        wait_time: JavaScript wait time in milliseconds
        extract_metadata: Whether to extract metadata
        **kwargs: Additional scraping options

    Returns:
        Task data dictionary
    """
    return {
        "source": {
            "source_type": "web",
            "query_parameters": {
                "urls": urls,
                "scraping_options": {
                    "wait_time": wait_time,
                    "extract_metadata": extract_metadata,
                    "include_links": kwargs.get("include_links", True),
                    "include_headings": kwargs.get("include_headings", True),
                    "follow_redirects": kwargs.get("follow_redirects", True),
                    "user_agent": kwargs.get("user_agent"),
                    "timeout": kwargs.get("timeout", 60000),
                },
            },
            "priority": kwargs.get("priority", 1),
            "timeout": kwargs.get("source_timeout", 120),
            "estimated_results": len(urls),
        },
        "plan_context": {
            "topic": kwargs.get("topic", "Web Content Research"),
            "plan_id": kwargs.get("plan_id"),
            "cognitive_processing": kwargs.get("cognitive_processing", True),
        },
        "task_type": task_type,
    }
