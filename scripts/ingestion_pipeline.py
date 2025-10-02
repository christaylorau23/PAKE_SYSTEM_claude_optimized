#!/usr/bin/env python3
"""
PAKE+ Universal Ingestion Pipeline
Multi-source content ingestion with automated processing
"""

import asyncio
import email
import hashlib
import imaplib
import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp
import feedparser

# Third-party imports
from bs4 import BeautifulSoup
from readability import Document

try:
    import textract

    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

if not TEXTRACT_AVAILABLE:
    logger.warning("textract not available - file processing will be limited")


@dataclass
class SourceConfig:
    """Configuration for an ingestion source"""

    name: str
    type: str  # 'rss', 'email', 'web', 'file', 'api'
    url: str | None = None
    credentials: dict[str, str] | None = None
    interval: int = 3600  # seconds
    enabled: bool = True
    filters: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class ContentItem:
    """Represents a piece of content to be ingested"""

    source_name: str
    source_type: str
    title: str
    content: str
    url: str
    published: datetime | None = None
    author: str | None = None
    tags: list[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.published is None:
            self.published = datetime.utcnow()


class UniversalIngestionPipeline:
    """Main ingestion pipeline coordinator"""

    def __init__(
        self,
        config_path: str = None,
        mcp_server_url: str = "http://localhost:8000",
    ):
        self.config_path = config_path or "configs/ingestion.json"
        self.mcp_server_url = mcp_server_url
        self.sources: list[SourceConfig] = []
        self.db_path = "data/ingestion.db"
        self.redis_client = None
        self.db_pool = None
        self.session = None

        # Ensure directories exist
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("configs", exist_ok=True)

        # Initialize local database for deduplication
        self._init_local_db()

    def _init_local_db(self):
        """Initialize SQLite database for tracking ingested content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ingested_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT UNIQUE NOT NULL,
                source_name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                published TIMESTAMP,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pake_id TEXT,
                status TEXT DEFAULT 'pending'
            )
        """,
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_content_hash ON ingested_content(content_hash)
        """,
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source ON ingested_content(source_name, source_type)
        """,
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_status ON ingested_content(status)
        """,
        )

        conn.commit()
        conn.close()

    async def initialize(self):
        """Initialize async resources"""
        # Initialize Redis connection
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            REDACTED_SECRET=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
        )

        # Initialize HTTP session
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "PAKE+ Ingestion Pipeline/1.0"},
        )

        # Load configuration
        await self.load_configuration()

        logger.info("Ingestion pipeline initialized")

    async def close(self):
        """Clean up async resources"""
        if self.session:
            await self.session.close()

    async def load_configuration(self):
        """Load source configurations from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path) as f:
                    config_data = json.load(f)

                self.sources = [
                    SourceConfig(**source_config)
                    for source_config in config_data.get("sources", [])
                ]

                logger.info(f"Loaded {len(self.sources)} source configurations")
            else:
                # Create default configuration
                await self._create_default_config()

        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            await self._create_default_config()

    async def _create_default_config(self):
        """Create default configuration file"""
        default_config = {
            "sources": [
                {
                    "name": "Hacker News",
                    "type": "rss",
                    "url": "https://news.ycombinator.com/rss",
                    "interval": 1800,
                    "enabled": True,
                    "filters": {"min_score": 10},
                },
                {
                    "name": "AI Research",
                    "type": "rss",
                    "url": "http://export.arxiv.org/rss/cs.AI",
                    "interval": 3600,
                    "enabled": True,
                    "tags": ["research", "ai"],
                },
                {
                    "name": "Personal Gmail",
                    "type": "email",
                    "credentials": {
                        "server": "imap.gmail.com",
                        "port": 993,
                        "username": "your-email@gmail.com",
                        "REDACTED_SECRET": "app-specific-REDACTED_SECRET",
                    },
                    "interval": 1800,
                    "enabled": False,
                    "filters": {"folders": ["INBOX"], "unread_only": True},
                },
            ],
            "global_settings": {
                "max_content_length": 50000,
                "min_content_length": 100,
                "default_confidence": 0.6,
                "enable_deduplication": True,
                "batch_size": 10,
            },
        }

        with open(self.config_path, "w") as f:
            json.dump(default_config, f, indent=2)

        logger.info(f"Created default configuration at {self.config_path}")
        await self.load_configuration()

    async def ingest_rss_feeds(self, source: SourceConfig) -> list[ContentItem]:
        """Ingest content from RSS feeds"""
        items = []

        try:
            logger.info(f"Ingesting RSS feed: {source.name}")

            async with self.session.get(source.url) as response:
                if response.status != 200:
                    logger.warning(
                        f"RSS feed {source.name} returned status {response.status}",
                    )
                    return items

                feed_data = await response.text()

            feed = feedparser.parse(feed_data)

            for entry in feed.entries:
                # Extract content
                content = entry.get("summary", "") or entry.get("description", "")
                if hasattr(entry, "content") and entry.content:
                    content = (
                        entry.content[0].value
                        if isinstance(entry.content, list)
                        else entry.content
                    )

                # Clean HTML if present
                if content and "<" in content:
                    soup = BeautifulSoup(content, "html.parser")
                    content = soup.get_text().strip()

                if not content or len(content) < 50:
                    continue

                # Parse published date
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])

                item = ContentItem(
                    source_name=source.name,
                    source_type="rss",
                    title=entry.get("title", "Untitled"),
                    content=content,
                    url=entry.get("link", ""),
                    published=published,
                    author=entry.get("author", ""),
                    tags=source.metadata.get("tags", []) if source.metadata else [],
                    metadata={
                        "feed_title": feed.feed.get("title", ""),
                        "feed_url": source.url,
                        "entry_id": entry.get("id", ""),
                    },
                )

                items.append(item)

            logger.info(f"Extracted {len(items)} items from {source.name}")

        except Exception as e:
            logger.error(f"Error ingesting RSS feed {source.name}: {e}")

        return items

    async def ingest_email(self, source: SourceConfig) -> list[ContentItem]:
        """Ingest emails from IMAP servers"""
        items = []

        if not source.credentials:
            logger.warning(f"No credentials provided for email source {source.name}")
            return items

        try:
            logger.info(f"Ingesting email: {source.name}")

            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(
                source.credentials["server"],
                source.credentials.get("port", 993),
            )
            mail.login(
                source.credentials["username"], source.credentials["REDACTED_SECRET"]
            )

            # Select folders to check
            folders = (
                source.filters.get("folders", ["INBOX"])
                if source.filters
                else ["INBOX"]
            )
            unread_only = (
                source.filters.get("unread_only", True) if source.filters else True
            )

            for folder in folders:
                try:
                    mail.select(folder)

                    # Search for emails
                    search_criteria = "UNSEEN" if unread_only else "ALL"
                    _, messages = mail.search(None, search_criteria)

                    message_ids = messages[0].split()

                    # Limit to recent messages
                    recent_messages = (
                        message_ids[-50:] if len(message_ids) > 50 else message_ids
                    )

                    for msg_id in recent_messages:
                        try:
                            _, msg_data = mail.fetch(msg_id, "(RFC822)")
                            email_body = msg_data[0][1]
                            email_message = email.message_from_bytes(email_body)

                            # Extract content
                            content = self._extract_email_content(email_message)
                            if not content or len(content) < 50:
                                continue

                            # Parse date
                            published = None
                            if email_message["Date"]:
                                try:
                                    published = email.utils.parsedate_to_datetime(
                                        email_message["Date"],
                                    )
                                except BaseException:
                                    pass

                            item = ContentItem(
                                source_name=source.name,
                                source_type="email",
                                title=email_message.get("Subject", "No Subject"),
                                content=content,
                                url=f"email://{email_message.get('Message-ID', msg_id)}",
                                published=published,
                                author=email_message.get("From", ""),
                                tags=(
                                    source.metadata.get("tags", [])
                                    if source.metadata
                                    else []
                                ),
                                metadata={
                                    "folder": folder,
                                    "message_id": email_message.get("Message-ID"),
                                    "to": email_message.get("To"),
                                    "cc": email_message.get("Cc"),
                                },
                            )

                            items.append(item)

                            # Mark as read if configured to do so
                            if unread_only:
                                mail.store(msg_id, "+FLAGS", "\\Seen")

                        except Exception as e:
                            logger.warning(f"Error processing email {msg_id}: {e}")

                except Exception as e:
                    logger.warning(f"Error accessing folder {folder}: {e}")

            mail.close()
            mail.logout()

            logger.info(f"Extracted {len(items)} emails from {source.name}")

        except Exception as e:
            logger.error(f"Error ingesting email {source.name}: {e}")

        return items

    def _extract_email_content(self, email_message) -> str:
        """Extract text content from email message"""
        content = ""

        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        content += payload.decode("utf-8", errors="ignore")
                elif part.get_content_type() == "text/html" and not content:
                    payload = part.get_payload(decode=True)
                    if payload:
                        soup = BeautifulSoup(
                            payload.decode("utf-8", errors="ignore"),
                            "html.parser",
                        )
                        content = soup.get_text()
        else:
            payload = email_message.get_payload(decode=True)
            if payload:
                content = payload.decode("utf-8", errors="ignore")

        # Clean up content
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)  # Reduce multiple newlines
        content = content.strip()

        return content

    async def ingest_web_content(self, source: SourceConfig) -> list[ContentItem]:
        """Scrape and ingest web content"""
        items = []

        try:
            logger.info(f"Ingesting web content: {source.name}")

            async with self.session.get(source.url) as response:
                if response.status != 200:
                    logger.warning(
                        f"Web source {source.name} returned status {response.status}",
                    )
                    return items

                html_content = await response.text()

            # Extract readable content using readability-lxml
            doc = Document(html_content)
            title = doc.title()
            content = doc.summary()

            # Convert to plain text
            soup = BeautifulSoup(content, "html.parser")
            text_content = soup.get_text().strip()

            if len(text_content) > 100:  # Minimum content length
                item = ContentItem(
                    source_name=source.name,
                    source_type="web",
                    title=title or "Web Content",
                    content=text_content,
                    url=source.url,
                    published=datetime.utcnow(),
                    metadata={
                        "scraped_at": datetime.utcnow().isoformat(),
                        "content_length": len(text_content),
                    },
                )

                items.append(item)

            logger.info(f"Extracted {len(items)} items from {source.name}")

        except Exception as e:
            logger.error(f"Error ingesting web content {source.name}: {e}")

        return items

    async def process_file_source(self, source: SourceConfig) -> list[ContentItem]:
        """Process files from a directory or specific file"""
        items = []

        try:
            file_path = Path(source.url.replace("file://", ""))

            if file_path.is_file():
                files_to_process = [file_path]
            elif file_path.is_dir():
                # Get files modified in last interval
                cutoff_time = datetime.now() - timedelta(seconds=source.interval)
                files_to_process = [
                    f
                    for f in file_path.rglob("*")
                    if f.is_file()
                    and f.suffix.lower() in [".txt", ".md", ".pdf", ".docx", ".doc"]
                    and datetime.fromtimestamp(f.stat().st_mtime) > cutoff_time
                ]
            else:
                logger.warning(f"File source path does not exist: {file_path}")
                return items

            for file_path in files_to_process:
                try:
                    # Extract content based on file type
                    if file_path.suffix.lower() in [".txt", ".md"]:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                    elif TEXTRACT_AVAILABLE:
                        # Use textract for other formats
                        content = textract.process(str(file_path)).decode(
                            "utf-8",
                            errors="ignore",
                        )
                    else:
                        logger.warning(
                            f"Skipping {file_path} - textract not available for format {file_path.suffix}",
                        )
                        continue

                    if len(content) > 100:
                        item = ContentItem(
                            source_name=source.name,
                            source_type="file",
                            title=file_path.stem,
                            content=content,
                            url=f"file://{file_path}",
                            published=datetime.fromtimestamp(file_path.stat().st_mtime),
                            metadata={
                                "file_path": str(file_path),
                                "file_size": file_path.stat().st_size,
                                "file_type": file_path.suffix,
                            },
                        )

                        items.append(item)

                except Exception as e:
                    logger.warning(f"Error processing file {file_path}: {e}")

            logger.info(f"Processed {len(items)} files from {source.name}")

        except Exception as e:
            logger.error(f"Error processing file source {source.name}: {e}")

        return items

    def _calculate_content_hash(self, item: ContentItem) -> str:
        """Calculate hash for content deduplication"""
        content_for_hash = f"{item.title}||{item.content[:1000]}||{item.url}"
        return hashlib.sha256(content_for_hash.encode()).hexdigest()

    def _is_duplicate_content(self, content_hash: str) -> bool:
        """Check if content has already been ingested"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM ingested_content WHERE content_hash = ?",
            (content_hash,),
        )

        result = cursor.fetchone()
        conn.close()

        return result is not None

    def _record_ingested_content(
        self,
        item: ContentItem,
        content_hash: str,
        pake_id: str,
    ):
        """Record content in local database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO ingested_content
                (content_hash, source_name, source_type, title, url, published, pake_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    content_hash,
                    item.source_name,
                    item.source_type,
                    item.title,
                    item.url,
                    item.published,
                    pake_id,
                    "processed",
                ),
            )

            conn.commit()

        except sqlite3.IntegrityError:
            # Already exists, update with pake_id
            cursor.execute(
                "UPDATE ingested_content SET pake_id = ?, status = ? WHERE content_hash = ?",
                (pake_id, "processed", content_hash),
            )
            conn.commit()

        finally:
            conn.close()

    async def send_to_mcp_server(self, item: ContentItem) -> str | None:
        """Send content item to MCP server for processing"""
        try:
            # Prepare payload
            payload = {
                "content": f"# {item.title}\n\n{item.content}",
                "source_uri": item.url,
                "metadata": {
                    **item.metadata,
                    "source_name": item.source_name,
                    "source_type": item.source_type,
                    "published": item.published.isoformat() if item.published else None,
                    "author": item.author,
                    "ingested_at": datetime.utcnow().isoformat(),
                },
                "tags": item.tags,
                "type": "note",
                "status": "draft",
                "verification_status": "pending",
                "confidence_score": 0.6,  # Default for external sources
            }

            async with self.session.post(
                f"{self.mcp_server_url}/ingest",
                json=payload,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("pake_id")
                logger.warning(
                    f"MCP server returned status {response.status} for {item.title}",
                )

        except Exception as e:
            logger.error(f"Error sending to MCP server: {e}")

        return None

    async def process_source(self, source: SourceConfig) -> int:
        """Process a single source and ingest its content"""
        if not source.enabled:
            return 0

        logger.info(f"Processing source: {source.name} ({source.type})")

        # Get content based on source type
        items = []

        if source.type == "rss":
            items = await self.ingest_rss_feeds(source)
        elif source.type == "email":
            items = await self.ingest_email(source)
        elif source.type == "web":
            items = await self.ingest_web_content(source)
        elif source.type == "file":
            items = await self.process_file_source(source)
        else:
            logger.warning(f"Unknown source type: {source.type}")
            return 0

        # Process and deduplicate items
        processed_count = 0

        for item in items:
            try:
                # Calculate content hash for deduplication
                content_hash = self._calculate_content_hash(item)

                # Skip if already processed
                if self._is_duplicate_content(content_hash):
                    logger.debug(f"Skipping duplicate content: {item.title}")
                    continue

                # Apply content filters
                if len(item.content) < 100:  # Minimum length
                    continue

                if len(item.content) > 50000:  # Maximum length
                    item.content = item.content[:50000] + "..."

                # Send to MCP server
                pake_id = await self.send_to_mcp_server(item)

                if pake_id:
                    # Record in local database
                    self._record_ingested_content(item, content_hash, pake_id)
                    processed_count += 1

                    logger.info(
                        f"Successfully ingested: {item.title} (PAKE ID: {pake_id})",
                    )

                    # Add to processing queue for potential follow-up actions
                    self.redis_client.lpush(
                        "ingestion_queue",
                        json.dumps(
                            {
                                "pake_id": pake_id,
                                "source_name": source.name,
                                "ingested_at": datetime.utcnow().isoformat(),
                            },
                        ),
                    )

            except Exception as e:
                logger.error(f"Error processing item {item.title}: {e}")

        logger.info(f"Processed {processed_count} new items from {source.name}")
        return processed_count

    async def run_single_cycle(self):
        """Run one ingestion cycle for all sources"""
        logger.info("Starting ingestion cycle")

        total_processed = 0

        for source in self.sources:
            try:
                processed = await self.process_source(source)
                total_processed += processed
            except Exception as e:
                logger.error(f"Error processing source {source.name}: {e}")

        logger.info(
            f"Ingestion cycle completed. Total items processed: {total_processed}",
        )

        # Update statistics in Redis
        stats = {
            "last_run": datetime.utcnow().isoformat(),
            "items_processed": total_processed,
            "sources_count": len(self.sources),
            "active_sources": len([s for s in self.sources if s.enabled]),
        }

        self.redis_client.set("ingestion_stats", json.dumps(stats))

        return total_processed

    async def run_continuous(self, min_interval: int = 300):
        """Run ingestion pipeline continuously"""
        logger.info("Starting continuous ingestion pipeline")

        while True:
            try:
                cycle_start = datetime.utcnow()
                await self.run_single_cycle()
                cycle_duration = (datetime.utcnow() - cycle_start).seconds

                # Wait for minimum interval
                sleep_time = max(min_interval - cycle_duration, 60)
                logger.info(f"Waiting {sleep_time} seconds until next cycle")

                await asyncio.sleep(sleep_time)

            except KeyboardInterrupt:
                logger.info("Ingestion pipeline stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in continuous ingestion: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    def get_ingestion_statistics(self) -> dict[str, Any]:
        """Get ingestion statistics from local database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total items by source
        cursor.execute(
            """
            SELECT source_name, source_type, COUNT(*) as count
            FROM ingested_content
            GROUP BY source_name, source_type
            ORDER BY count DESC
        """,
        )

        by_source = cursor.fetchall()

        # Items by date
        cursor.execute(
            """
            SELECT DATE(ingested_at) as date, COUNT(*) as count
            FROM ingested_content
            WHERE ingested_at >= date('now', '-30 days')
            GROUP BY DATE(ingested_at)
            ORDER BY date DESC
        """,
        )

        by_date = cursor.fetchall()

        # Total stats
        cursor.execute("SELECT COUNT(*) FROM ingested_content")
        total_items = cursor.fetchone()[0]

        cursor.execute(
            'SELECT COUNT(*) FROM ingested_content WHERE status = "processed"',
        )
        processed_items = cursor.fetchone()[0]

        conn.close()

        return {
            "total_items": total_items,
            "processed_items": processed_items,
            "by_source": [
                {"name": row[0], "type": row[1], "count": row[2]} for row in by_source
            ],
            "by_date": [{"date": row[0], "count": row[1]} for row in by_date],
            "sources_configured": len(self.sources),
            "sources_enabled": len([s for s in self.sources if s.enabled]),
        }


async def main():
    """Main function for running the ingestion pipeline"""
    import argparse

    parser = argparse.ArgumentParser(description="PAKE+ Universal Ingestion Pipeline")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument(
        "--mcp-url",
        default="http://localhost:8000",
        help="MCP server URL",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Run single cycle instead of continuous",
    )
    parser.add_argument("--stats", action="store_true", help="Show statistics and exit")

    args = parser.parse_args()

    pipeline = UniversalIngestionPipeline(
        config_path=args.config,
        mcp_server_url=args.mcp_url,
    )

    try:
        await pipeline.initialize()

        if args.stats:
            stats = pipeline.get_ingestion_statistics()
            print(json.dumps(stats, indent=2))
            return

        if args.single:
            processed = await pipeline.run_single_cycle()
            print(f"Processed {processed} items")
        else:
            await pipeline.run_continuous()

    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
