#!/usr/bin/env python3
"""PAKE System - Phase 2B RSS/Atom Feed Service Implementation
GREEN phase: Minimal implementation to pass TDD tests

Following TDD methodology for RSS/Atom feed ingestion with cognitive integration.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import aiohttp
import feedparser

# Import shared components
from scripts.ingestion_pipeline import ContentItem

# Configure logging
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RSSError:
    """Immutable error class for RSS service errors"""

    message: str
    error_code: str = "UNKNOWN_ERROR"
    retry_after: int | None = None
    feed_url: str | None = None

    @property
    def is_retryable(self) -> bool:
        """Determine if error is retryable based on error code"""
        retryable_codes = ["NETWORK_ERROR", "TIMEOUT", "SERVER_ERROR", "RATE_LIMIT"]
        return self.error_code in retryable_codes


@dataclass(frozen=True)
class RSSFeedItem:
    """Immutable RSS/Atom feed item"""

    title: str
    link: str
    description: str
    published: datetime
    guid: str
    author: str | None = None
    categories: list[str] = field(default_factory=list)
    full_content: str | None = None
    cognitive_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class RSSFeedQuery:
    """Query configuration for RSS feed fetching"""

    feed_urls: list[str]
    max_items_per_feed: int = 10
    fetch_full_content: bool = False
    date_from: datetime | None = None
    date_to: datetime | None = None
    keywords: list[str] = field(default_factory=list)
    keyword_match_mode: str = "any"  # "any" or "all"
    enable_cognitive_assessment: bool = False


@dataclass
class RSSFeedResult:
    """Result from RSS feed fetching operation"""

    success: bool
    feed_url: str
    feed_title: str | None = None
    items: list[RSSFeedItem] = field(default_factory=list)
    error: RSSError | None = None
    feeds_processed: int = 0
    feeds_failed: int = 0
    cognitive_assessment_applied: bool = False
    from_cache: bool = False
    fetch_time: float = 0.0


class RSSFeedService:
    """Phase 2B RSS/Atom Feed Service

    Provides comprehensive RSS and Atom feed ingestion with cognitive processing,
    caching, filtering, and integration with the PAKE orchestrator.
    """

    def __init__(self):
        """Initialize RSS feed service"""
        self.session: aiohttp.ClientSession | None = None
        self.cache: dict[str, dict[str, Any]] = {}
        self.cache_ttl = timedelta(minutes=30)  # 30 minute cache TTL

        # Rate limiting
        self.rate_limit_delay = 0.1  # 100ms between requests
        self.last_request_time = 0.0

        logger.info("RSSFeedService initialized")

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "PAKE-RSS-Bot/1.0 (+https://example.com/bot)"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _get_session(self):
        """Get or create HTTP session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "PAKE-RSS-Bot/1.0 (+https://example.com/bot)"},
            )
        return self.session

    async def fetch_feed(
        self,
        feed_url: str,
        max_retries: int = 3,
        enable_caching: bool = True,
        rate_limit_delay: float | None = None,
    ) -> RSSFeedResult:
        """Fetch and parse RSS/Atom feed from URL"""
        logger.info(f"Fetching RSS feed: {feed_url}")

        # Check cache first
        if enable_caching:
            cached_result = self._get_cached_result(feed_url)
            if cached_result:
                return cached_result

        # Apply rate limiting
        if rate_limit_delay or self.rate_limit_delay:
            delay = (
                rate_limit_delay
                if rate_limit_delay is not None
                else self.rate_limit_delay
            )
            await self._apply_rate_limit(delay)

        # Validate URL
        if not self._is_valid_url(feed_url):
            return RSSFeedResult(
                success=False,
                feed_url=feed_url,
                error=RSSError(
                    message=f"Invalid URL: {feed_url}",
                    error_code="INVALID_URL",
                    feed_url=feed_url,
                ),
            )

        # Fetch with retry logic
        for attempt in range(max_retries + 1):
            try:
                start_time = asyncio.get_event_loop().time()

                session = self._get_session()
                async with session.get(feed_url) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        result = await self._parse_feed_content(xml_content, feed_url)

                        # Calculate fetch time
                        result.fetch_time = asyncio.get_event_loop().time() - start_time

                        # Cache successful result
                        if enable_caching and result.success:
                            self._cache_result(feed_url, result)

                        return result

                    if response.status == 404:
                        return RSSFeedResult(
                            success=False,
                            feed_url=feed_url,
                            error=RSSError(
                                message=f"Feed not found: {feed_url}",
                                error_code="NOT_FOUND",
                                feed_url=feed_url,
                            ),
                        )

                    if response.status in [429, 503]:
                        # Rate limiting or server overload
                        retry_after = int(response.headers.get("Retry-After", 60))
                        if attempt < max_retries:
                            logger.warning(
                                f"Rate limited, waiting {retry_after}s before retry",
                            )
                            await asyncio.sleep(retry_after)
                            continue

                        return RSSFeedResult(
                            success=False,
                            feed_url=feed_url,
                            error=RSSError(
                                message=f"Rate limited: {feed_url}",
                                error_code="RATE_LIMIT",
                                retry_after=retry_after,
                                feed_url=feed_url,
                            ),
                        )

                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                    )

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {feed_url}: {e}")

                if attempt < max_retries:
                    # Exponential backoff
                    wait_time = (2**attempt) + (attempt * 0.1)
                    await asyncio.sleep(wait_time)
                else:
                    # Final failure
                    error_code = "NETWORK_ERROR"
                    if "timeout" in str(e).lower():
                        error_code = "TIMEOUT"
                    elif "parse" in str(e).lower():
                        error_code = "PARSE_ERROR"

                    return RSSFeedResult(
                        success=False,
                        feed_url=feed_url,
                        error=RSSError(
                            message=str(e),
                            error_code=error_code,
                            feed_url=feed_url,
                        ),
                    )

        # Shouldn't reach here, but just in case
        return RSSFeedResult(
            success=False,
            feed_url=feed_url,
            error=RSSError(
                message="Max retries exceeded",
                error_code="MAX_RETRIES",
                feed_url=feed_url,
            ),
        )

    async def _parse_feed_content(
        self,
        xml_content: str,
        feed_url: str,
    ) -> RSSFeedResult:
        """Parse RSS/Atom XML content into structured format"""
        try:
            # Use feedparser for robust RSS/Atom parsing
            parsed = feedparser.parse(xml_content)

            if parsed.bozo and parsed.bozo_exception:
                # Parsing errors detected
                return RSSFeedResult(
                    success=False,
                    feed_url=feed_url,
                    error=RSSError(
                        message=f"XML parsing error: {parsed.bozo_exception}",
                        error_code="PARSE_ERROR",
                        feed_url=feed_url,
                    ),
                )

            # Extract feed metadata
            feed_title = parsed.feed.get("title", "Unknown Feed")

            # Parse items
            items = []
            for entry in parsed.entries:
                try:
                    # Extract published date
                    published = datetime.now(UTC)
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        import time

                        published = datetime.fromtimestamp(
                            time.mktime(entry.published_parsed),
                            tz=UTC,
                        )

                    # Extract categories
                    categories = []
                    if hasattr(entry, "tags"):
                        categories = [tag.term for tag in entry.tags]
                    elif hasattr(entry, "category"):
                        categories = (
                            [entry.category] if isinstance(entry.category, str) else []
                        )

                    # Create RSS item
                    item = RSSFeedItem(
                        title=entry.get("title", "Untitled"),
                        link=entry.get("link", ""),
                        description=entry.get("description", "")
                        or entry.get("summary", ""),
                        published=published,
                        guid=entry.get(
                            "id",
                            entry.get(
                                "link",
                                f"item-{len(items)}",
                            ),
                        ),
                        author=entry.get("author", None),
                        categories=categories,
                    )

                    items.append(item)

                except Exception as item_error:
                    logger.warning(f"Failed to parse item in {feed_url}: {item_error}")
                    continue

            return RSSFeedResult(
                success=True,
                feed_url=feed_url,
                feed_title=feed_title,
                items=items,
            )

        except Exception as e:
            logger.error(f"Failed to parse feed {feed_url}: {e}")
            return RSSFeedResult(
                success=False,
                feed_url=feed_url,
                error=RSSError(
                    message=f"Feed parsing failed: {str(e)}",
                    error_code="PARSE_ERROR",
                    feed_url=feed_url,
                ),
            )

    async def fetch_multiple_feeds(self, query: RSSFeedQuery) -> RSSFeedResult:
        """Fetch multiple RSS feeds concurrently"""
        logger.info(f"Fetching {len(query.feed_urls)} feeds concurrently")

        # Create concurrent tasks
        tasks = []
        for feed_url in query.feed_urls:
            task = self.fetch_feed(feed_url)
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        all_items = []
        feeds_processed = 0
        feeds_failed = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                feeds_failed += 1
                logger.error(f"Failed to fetch {query.feed_urls[i]}: {result}")
                continue

            if result.success:
                feeds_processed += 1

                # Apply filtering
                filtered_items = self._filter_items(result.items, query)

                # Limit items per feed
                if query.max_items_per_feed > 0:
                    filtered_items = filtered_items[: query.max_items_per_feed]

                all_items.extend(filtered_items)
            else:
                feeds_failed += 1

        # Return aggregated result
        return RSSFeedResult(
            success=feeds_processed > 0,
            feed_url="multiple_feeds",
            feed_title=f"Aggregated from {len(query.feed_urls)} feeds",
            items=all_items,
            feeds_processed=feeds_processed,
            feeds_failed=feeds_failed,
        )

    async def fetch_with_query(self, query: RSSFeedQuery) -> RSSFeedResult:
        """Fetch RSS feeds with advanced query filtering"""
        # First fetch the feeds
        result = await self.fetch_multiple_feeds(query)

        if not result.success or not result.items:
            return result

        # Apply filtering
        filtered_items = self._filter_items(result.items, query)

        # Limit items per feed if specified
        if query.max_items_per_feed and query.max_items_per_feed > 0:
            filtered_items = filtered_items[: query.max_items_per_feed]

        # Fetch full content if requested
        if query.fetch_full_content:
            enhanced_items = []
            for item in filtered_items:
                if item.link:
                    full_content = await self.fetch_article_content(item.link)
                    enhanced_item = RSSFeedItem(
                        title=item.title,
                        link=item.link,
                        description=item.description,
                        published=item.published,
                        guid=item.guid,
                        author=item.author,
                        categories=item.categories,
                        full_content=full_content,
                        cognitive_metadata=item.cognitive_metadata,
                    )
                    enhanced_items.append(enhanced_item)
                else:
                    enhanced_items.append(item)
            filtered_items = enhanced_items

        return RSSFeedResult(
            success=result.success,
            feed_url=result.feed_url,
            feed_title=result.feed_title,
            items=filtered_items,
            error=result.error,
        )

    def _filter_items(
        self,
        items: list[RSSFeedItem],
        query: RSSFeedQuery,
    ) -> list[RSSFeedItem]:
        """Apply filtering to RSS feed items based on query parameters"""
        filtered_items = items

        # Date range filtering
        if query.date_from or query.date_to:
            date_filtered = []
            for item in filtered_items:
                item_date = item.published

                # Check date_from
                if query.date_from and item_date < query.date_from:
                    continue

                # Check date_to
                if query.date_to and item_date > query.date_to:
                    continue

                date_filtered.append(item)

            filtered_items = date_filtered

        # Keyword filtering
        if query.keywords:
            keyword_filtered = []
            for item in filtered_items:
                # Combine title and description for keyword matching
                text_content = f"{item.title} {item.description}".lower()

                if query.keyword_match_mode == "any":
                    # Match any keyword
                    if any(
                        keyword.lower() in text_content for keyword in query.keywords
                    ):
                        keyword_filtered.append(item)
                else:
                    # Match all keywords
                    if all(
                        keyword.lower() in text_content for keyword in query.keywords
                    ):
                        keyword_filtered.append(item)

            filtered_items = keyword_filtered

        return filtered_items

    async def fetch_article_content(self, article_url: str) -> str | None:
        """Fetch full article content from URL (basic implementation)"""
        try:
            session = self._get_session()
            async with session.get(article_url) as response:
                if response.status == 200:
                    html_content = await response.text()
                    # Basic content extraction (could be enhanced with newspaper3k or similar)
                    # For now, return raw HTML
                    return html_content[:5000]  # Truncate for safety
        except Exception as e:
            logger.warning(f"Failed to fetch article content from {article_url}: {e}")

        return None

    async def fetch_with_cognitive_assessment(
        self,
        query: RSSFeedQuery,
        cognitive_engine,
    ) -> RSSFeedResult:
        """Fetch RSS feeds with cognitive assessment applied"""
        # First fetch the feeds normally
        result = await self.fetch_with_query(query)

        if not result.success or not result.items:
            return result

        # Apply cognitive assessment to each item
        assessed_items = []
        for item in result.items:
            try:
                # Prepare content for cognitive assessment
                content_text = f"{item.title}\n\n{item.description}"
                if item.full_content:
                    content_text += f"\n\n{item.full_content}"

                # Apply cognitive assessment
                quality_score = await cognitive_engine.assess_content_quality(
                    content_text,
                )
                categories = await cognitive_engine.categorize_content(content_text)
                insights = await cognitive_engine.extract_insights(content_text)

                # Create enhanced item with cognitive metadata
                cognitive_metadata = {
                    "quality_score": quality_score,
                    "categories": categories,
                    "insights": insights,
                }

                enhanced_item = RSSFeedItem(
                    title=item.title,
                    link=item.link,
                    description=item.description,
                    published=item.published,
                    guid=item.guid,
                    author=item.author,
                    categories=item.categories,
                    full_content=item.full_content,
                    cognitive_metadata=cognitive_metadata,
                )

                assessed_items.append(enhanced_item)

            except Exception as e:
                logger.warning(
                    f"Cognitive assessment failed for item {item.title}: {e}",
                )
                # Keep original item if assessment fails
                assessed_items.append(item)

        # Return result with cognitive assessment applied
        enhanced_result = RSSFeedResult(
            success=result.success,
            feed_url=result.feed_url,
            feed_title=result.feed_title,
            items=assessed_items,
            error=result.error,
            feeds_processed=result.feeds_processed,
            feeds_failed=result.feeds_failed,
            cognitive_assessment_applied=True,
            from_cache=result.from_cache,
            fetch_time=result.fetch_time,
        )

        return enhanced_result

    async def to_content_items(
        self,
        rss_result: RSSFeedResult,
        source_name: str,
    ) -> list[ContentItem]:
        """Convert RSS feed items to standardized ContentItem format"""
        content_items = []

        for item in rss_result.items:
            try:
                # Prepare content
                content = item.description
                if item.full_content:
                    content = item.full_content

                # Prepare metadata
                metadata = {
                    "feed_title": rss_result.feed_title,
                    "guid": item.guid,
                    "categories": item.categories,
                }

                # Add cognitive metadata if available
                if item.cognitive_metadata:
                    metadata.update(item.cognitive_metadata)

                # Create ContentItem
                content_item = ContentItem(
                    source_name=source_name,
                    source_type="rss",
                    title=item.title,
                    content=content,
                    url=item.link,
                    published=item.published,
                    author=item.author,
                    tags=item.categories,
                    metadata=metadata,
                )

                content_items.append(content_item)

            except Exception as e:
                logger.warning(f"Failed to convert RSS item to ContentItem: {e}")
                continue

        logger.info(f"Converted {len(content_items)} RSS items to ContentItems")
        return content_items

    async def execute_ingestion_query(
        self,
        query: RSSFeedQuery,
        source_name: str,
    ) -> list[ContentItem]:
        """Execute RSS ingestion query and return ContentItem list (orchestrator compatible)"""
        # Fetch feeds with query
        result = await self.fetch_with_query(query)

        if not result.success:
            logger.error(f"RSS ingestion failed: {result.error}")
            return []

        # Convert to ContentItems
        return await self.to_content_items(result, source_name)

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def _get_cached_result(self, feed_url: str) -> RSSFeedResult | None:
        """Get cached result if valid"""
        cache_key = hashlib.sha256(feed_url.encode()).hexdigest()

        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            cache_time = cache_entry["timestamp"]

            # Check if cache is still valid
            if datetime.now(UTC) - cache_time < self.cache_ttl:
                result = cache_entry["result"]
                result.from_cache = True
                return result
            # Remove expired cache entry
            del self.cache[cache_key]

        return None

    def _cache_result(self, feed_url: str, result: RSSFeedResult):
        """Cache successful result"""
        cache_key = hashlib.sha256(feed_url.encode()).hexdigest()

        self.cache[cache_key] = {
            "timestamp": datetime.now(UTC),
            "result": result,
        }

        # Limit cache size (basic LRU-like behavior)
        if len(self.cache) > 100:
            # Remove oldest entries
            oldest_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k]["timestamp"],
            )[:10]

            for key in oldest_keys:
                del self.cache[key]

    async def _apply_rate_limit(self, delay: float):
        """Apply rate limiting delay"""
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - self.last_request_time

        if elapsed < delay:
            wait_time = delay - elapsed
            await asyncio.sleep(wait_time)

        self.last_request_time = asyncio.get_event_loop().time()

    async def clear_cache(self):
        """Clear RSS feed cache"""
        self.cache.clear()
        logger.info("RSS feed cache cleared")

    async def health_check(self) -> dict[str, Any]:
        """Perform RSS service health check"""
        return {
            "status": "healthy",
            "cache_entries": len(self.cache),
            "cache_ttl_minutes": self.cache_ttl.total_seconds() / 60,
            "rate_limit_delay_ms": self.rate_limit_delay * 1000,
        }
