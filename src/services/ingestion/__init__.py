#!/usr/bin/env python3
"""PAKE System - Ingestion Services Package
Phase 2A: Enhanced omni-source ingestion capabilities
"""

from .arxiv_enhanced_service import (
    ArxivEnhancedService,
    ArxivError,
    ArxivPaper,
    ArxivResult,
    ArxivSearchQuery,
)
from .firecrawl_service import (
    FirecrawlError,
    FirecrawlResult,
    FirecrawlService,
    ScrapingOptions,
)
from .pubmed_service import (
    PubMedAuthor,
    PubMedError,
    PubMedJournal,
    PubMedPaper,
    PubMedResult,
    PubMedSearchQuery,
    PubMedService,
)

__all__ = [
    "FirecrawlService",
    "FirecrawlResult",
    "FirecrawlError",
    "ScrapingOptions",
    "ArxivEnhancedService",
    "ArxivResult",
    "ArxivError",
    "ArxivSearchQuery",
    "ArxivPaper",
    "PubMedService",
    "PubMedResult",
    "PubMedError",
    "PubMedSearchQuery",
    "PubMedPaper",
    "PubMedAuthor",
    "PubMedJournal",
]
