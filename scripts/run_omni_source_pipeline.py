#!/usr/bin/env python3
"""
PAKE+ Omni-Source Research Pipeline
Automated deployment script for Phase 2A multi-source ingestion system

Usage:
    python scripts/run_omni_source_pipeline.py "machine learning in healthcare"
    python scripts/run_omni_source_pipeline.py "artificial intelligence" --save-to-vault
"""

import argparse
import asyncio
import json

# Add services to path
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from services.ingestion.orchestrator import IngestionConfig, IngestionOrchestrator

project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)


async def run_omni_source_research(
    topic: str,
    context: dict[str, Any] = None,
    save_to_vault: bool = False,
):
    """
    Execute comprehensive omni-source research ingestion

    Args:
        topic: Research topic to investigate
        context: Additional context for the research
        save_to_vault: Whether to save results to Obsidian vault
    """

    print("🚀 PAKE+ Omni-Source Research Pipeline")
    print(f"📊 Topic: {topic}")
    print("=" * 60)

    # Create optimized configuration
    config = IngestionConfig(
        max_concurrent_sources=3,
        timeout_per_source=120,
        quality_threshold=0.7,
        enable_cognitive_processing=True,
        enable_workflow_automation=True,
        deduplication_enabled=True,
        caching_enabled=True,
    )

    # Initialize orchestrator
    orchestrator = IngestionOrchestrator(config=config)

    # Create ingestion plan
    print("📋 Creating comprehensive ingestion plan...")

    if context is None:
        context = {
            "urgency": "medium",
            "domain": "research",
            "quality_threshold": 0.7,
            "enable_query_optimization": True,
        }

    plan = await orchestrator.create_ingestion_plan(topic, context)

    print("✅ Plan created:")
    print(f"   • Sources: {len(plan.sources)}")
    print(f"   • Estimated results: {plan.estimated_total_results}")
    print(f"   • Estimated time: {plan.estimated_duration}s")
    print()

    # Show source breakdown
    for i, source in enumerate(plan.sources, 1):
        print(
            f"   {i}. {source.source_type.upper()}: {
                source.estimated_results
            } results expected",
        )

    print()
    print("🔄 Executing ingestion plan...")

    # Execute the plan
    result = await orchestrator.execute_ingestion_plan(plan)

    print("✅ Execution completed!")
    print(f"   • Success: {result.success}")
    print(f"   • Items collected: {len(result.content_items)}")
    print(f"   • Sources used: {len(result.source_results)}")
    print(f"   • Processing time: {result.processing_time_seconds:.2f}s")
    print()

    # Show detailed results
    print("📊 Detailed Results:")
    for source_result in result.source_results:
        status = "✅" if source_result.success else "❌"
        print(
            f"   {status} {source_result.source_type}: {
                len(source_result.content_items)
            } items",
        )
        if not source_result.success and source_result.error:
            print(f"      Error: {source_result.error}")

    print()

    # Show content summary
    if result.content_items:
        print("📄 Content Summary:")
        for i, item in enumerate(result.content_items[:5], 1):  # Show first 5 items
            print(f"   {i}. {item.title[:60]}...")
            print(f"      Source: {item.source}")
            print(f"      Quality: {item.confidence_score:.2f}")
            print()

        if len(result.content_items) > 5:
            print(f"   ... and {len(result.content_items) - 5} more items")
            print()

    # Save to vault if requested
    if save_to_vault:
        await save_results_to_vault(topic, result)

    # Save results to JSON for further processing
    results_file = (
        f"omni_source_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    # Convert result to serializable format
    results_data = {
        "topic": topic,
        "timestamp": datetime.now().isoformat(),
        "success": result.success,
        "total_items": len(result.content_items),
        "processing_time": result.processing_time_seconds,
        "source_results": [
            {
                "source_type": sr.source_type,
                "success": sr.success,
                "items_count": len(sr.content_items),
                "error": sr.error,
            }
            for sr in result.source_results
        ],
        "content_items": [
            {
                "title": item.title,
                "source": item.source,
                "content_preview": item.content[:200] if item.content else "",
                "confidence_score": item.confidence_score,
                "url": getattr(item, "url", None),
                "authors": getattr(item, "authors", []),
                "publication_date": getattr(item, "publication_date", None),
            }
            for item in result.content_items
        ],
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2, default=str)

    print(f"💾 Results saved to: {results_file}")

    return result


async def save_results_to_vault(topic: str, result):
    """Save research results to Obsidian vault"""

    print("💾 Saving results to Obsidian vault...")

    # Create note content
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    filename = f"omni-source-research-{datetime.now().strftime('%Y-%m-%d')}-{
        topic.replace(' ', '-')[:30]
    }.md"

    content = f"""---
title: "Omni-Source Research: {topic}"
created: {timestamp}
type: research
source: omni-source-pipeline
tags: [research, omni-source, automated]
topic: "{topic}"
total_sources: {len(result.source_results)}
total_items: {len(result.content_items)}
processing_time: {result.processing_time_seconds:.2f}s
---

# Omni-Source Research: {topic}

**Generated:** {timestamp}
**Sources:** {len(result.source_results)} ({
        ", ".join(sr.source_type for sr in result.source_results)
    })
**Items Found:** {len(result.content_items)}
**Processing Time:** {result.processing_time_seconds:.2f}s

## Summary

This research was automatically generated using the PAKE+ omni-source ingestion pipeline, which simultaneously searched across web sources, academic papers (ArXiv), and biomedical literature (PubMed).

## Source Results

"""

    for source_result in result.source_results:
        status = "✅ Success" if source_result.success else "❌ Failed"
        content += f"### {source_result.source_type.upper()} - {status}\n\n"
        content += f"- **Items found:** {len(source_result.content_items)}\n"
        if not source_result.success and source_result.error:
            content += f"- **Error:** {source_result.error}\n"
        content += "\n"

    # Add content items
    content += "## Research Results\n\n"

    for i, item in enumerate(result.content_items, 1):
        content += f"### {i}. {item.title}\n\n"
        content += f"**Source:** {item.source}  \n"
        content += f"**Quality Score:** {item.confidence_score:.2f}  \n"

        if hasattr(item, "url") and item.url:
            content += f"**URL:** {item.url}  \n"
        if hasattr(item, "authors") and item.authors:
            content += f"**Authors:** {', '.join(item.authors)}  \n"
        if hasattr(item, "publication_date") and item.publication_date:
            content += f"**Published:** {item.publication_date}  \n"

        content += "\n"

        if item.content:
            # Add excerpt
            excerpt = item.content[:500].strip()
            if len(item.content) > 500:
                excerpt += "..."
            content += f"**Excerpt:**\n{excerpt}\n\n"

        content += "---\n\n"

    # Save to vault
    vault_path = Path("D:/Knowledge-Vault/00-Inbox")
    vault_path.mkdir(parents=True, exist_ok=True)

    note_path = vault_path / filename
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Research note saved to: {note_path}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE+ Omni-Source Research Pipeline")
    parser.add_argument("topic", help="Research topic to investigate")
    parser.add_argument(
        "--save-to-vault",
        action="store_true",
        help="Save results to Obsidian vault",
    )
    parser.add_argument("--domain", help="Research domain context")
    parser.add_argument(
        "--urgency",
        choices=["low", "medium", "high"],
        default="medium",
        help="Research urgency",
    )
    parser.add_argument(
        "--quality-threshold",
        type=float,
        default=0.7,
        help="Minimum quality threshold",
    )

    args = parser.parse_args()

    # Build context
    context = {
        "urgency": args.urgency,
        "domain": args.domain or "general",
        "quality_threshold": args.quality_threshold,
        "enable_query_optimization": True,
    }

    try:
        result = await run_omni_source_research(
            topic=args.topic,
            context=context,
            save_to_vault=args.save_to_vault,
        )

        if result.success:
            print("\n🎉 Research pipeline completed successfully!")
            print(
                f"📊 {len(result.content_items)} high-quality research items collected",
            )
        else:
            print("\n⚠️  Research pipeline completed with some issues")
            print(f"📊 {len(result.content_items)} items collected")

    except Exception as e:
        print(f"\n❌ Error running research pipeline: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
