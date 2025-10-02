#!/usr/bin/env python3
"""PAKE System - Source Executor
Single Responsibility: Executing ingestion from individual sources
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any

from ..interfaces import (
    IngestionSource,
    IngestionPlan,
    ContentItem,
    SourceExecutorInterface,
)
from ..shared_utils import generate_cache_key, create_error_detail
from ..firecrawl_service import FirecrawlService, ScrapingOptions
from ..arxiv_enhanced_service import ArxivEnhancedService, ArxivSearchQuery
from ..pubmed_service import PubMedService, PubMedSearchQuery

logger = logging.getLogger(__name__)


class SourceExecutor(SourceExecutorInterface):
    """Single Responsibility: Executing ingestion from individual sources"""
    
    def __init__(self):
        # Initialize source services
        self.firecrawl_service = FirecrawlService()
        self.arxiv_service = ArxivEnhancedService()
        self.pubmed_service = PubMedService()
    
    async def execute_source(
        self,
        source: IngestionSource,
        plan: IngestionPlan,
    ) -> tuple[list[ContentItem], dict[str, Any]]:
        """Execute ingestion for a single source"""
        
        logger.info(f"Executing source {source.source_type} (ID: {source.source_id})")
        
        start_time = time.time()
        content_items = []
        metrics = {
            "source_id": source.source_id,
            "source_type": source.source_type,
            "start_time": start_time,
            "success": False,
            "error": None,
            "items_retrieved": 0,
            "processing_time_ms": 0,
        }
        
        try:
            # Execute based on source type
            if source.source_type == "web":
                content_items = await self._execute_web_source(source)
            elif source.source_type == "arxiv":
                content_items = await self._execute_arxiv_source(source)
            elif source.source_type == "pubmed":
                content_items = await self._execute_pubmed_source(source)
            else:
                raise ValueError(f"Unsupported source type: {source.source_type}")
            
            # Update metrics
            metrics["success"] = True
            metrics["items_retrieved"] = len(content_items)
            metrics["processing_time_ms"] = (time.time() - start_time) * 1000
            
            logger.info(f"Source execution completed", {
                "source_id": source.source_id,
                "items_retrieved": len(content_items),
                "processing_time_ms": metrics["processing_time_ms"],
            })
            
        except Exception as e:
            metrics["error"] = str(e)
            metrics["processing_time_ms"] = (time.time() - start_time) * 1000
            
            logger.error(f"Source execution failed", {
                "source_id": source.source_id,
                "error": str(e),
            })
            
            raise
        
        return content_items, metrics
    
    async def _execute_web_source(self, source: IngestionSource) -> list[ContentItem]:
        """Execute web source ingestion"""
        
        query = source.query_parameters.get("query", "")
        max_results = source.query_parameters.get("max_results", source.estimated_results)
        
        # Configure scraping options
        scraping_options = ScrapingOptions(
            formats=["markdown"],
            onlyMainContent=True,
            maxPages=max_results,
        )
        
        # Execute web scraping
        results = await self.firecrawl_service.scrape_urls(
            urls=[query],  # Assuming query is a URL
            options=scraping_options,
        )
        
        # Convert to ContentItem format
        content_items = []
        for result in results:
            content_item = ContentItem(
                title=result.get("title", "Untitled"),
                content=result.get("markdown", ""),
                url=result.get("url", ""),
                source_type="web",
                metadata={
                    "scraped_at": result.get("scraped_at"),
                    "word_count": len(result.get("markdown", "").split()),
                },
            )
            content_items.append(content_item)
        
        return content_items
    
    async def _execute_arxiv_source(self, source: IngestionSource) -> list[ContentItem]:
        """Execute ArXiv source ingestion"""
        
        query = source.query_parameters.get("query", "")
        max_results = source.query_parameters.get("max_results", source.estimated_results)
        
        # Create search query
        search_query = ArxivSearchQuery(
            query=query,
            max_results=max_results,
            sort_by="relevance",
        )
        
        # Execute ArXiv search
        results = await self.arxiv_service.search_papers(search_query)
        
        # Convert to ContentItem format
        content_items = []
        for result in results:
            content_item = ContentItem(
                title=result.get("title", "Untitled"),
                content=result.get("abstract", ""),
                url=result.get("url", ""),
                source_type="arxiv",
                metadata={
                    "authors": result.get("authors", []),
                    "published_date": result.get("published", ""),
                    "categories": result.get("categories", []),
                },
            )
            content_items.append(content_item)
        
        return content_items
    
    async def _execute_pubmed_source(self, source: IngestionSource) -> list[ContentItem]:
        """Execute PubMed source ingestion"""
        
        query = source.query_parameters.get("query", "")
        max_results = source.query_parameters.get("max_results", source.estimated_results)
        
        # Create search query
        search_query = PubMedSearchQuery(
            query=query,
            max_results=max_results,
            sort_by="relevance",
        )
        
        # Execute PubMed search
        results = await self.pubmed_service.search_papers(search_query)
        
        # Convert to ContentItem format
        content_items = []
        for result in results:
            content_item = ContentItem(
                title=result.get("title", "Untitled"),
                content=result.get("abstract", ""),
                url=result.get("url", ""),
                source_type="pubmed",
                metadata={
                    "authors": result.get("authors", []),
                    "published_date": result.get("published", ""),
                    "journal": result.get("journal", ""),
                },
            )
            content_items.append(content_item)
        
        return content_items
    
    def get_source_cache_key(self, source: IngestionSource) -> str:
        """Generate cache key for source execution"""
        
        # Create deterministic cache key based on source parameters
        cache_data = {
            "source_type": source.source_type,
            "query_parameters": source.query_parameters,
            "estimated_results": source.estimated_results,
        }
        
        return generate_cache_key(cache_data, source.source_type)
