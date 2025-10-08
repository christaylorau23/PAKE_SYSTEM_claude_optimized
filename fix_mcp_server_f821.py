#!/usr/bin/env python3
"""F821 Error Fix Script for mcp_server_standalone.py
Fixes missing function parameters and incorrect FastAPI endpoint signatures.
"""

from pathlib import Path
import re
from typing import Dict, List, Tuple


def fix_fastapi_endpoints(file_path: Path) -> tuple[bool, int]:
    """Fix FastAPI endpoint function signatures."""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    original_content = content
    fixes_applied = 0

    # Define endpoint fixes - mapping from function name to proper parameters
    endpoint_fixes = {
        "perform_search": "search_request: SearchRequest",
        "quick_search": "search_request: SearchRequest",
        "summarize_content": "summarize_request: SummarizeRequest",
        "get_summarization_analytics": "",
        "get_ml_dashboard_data": "",
        "get_knowledge_insights": "",
        "get_research_patterns": "",
        "get_dashboard_metrics": "",
        "get_knowledge_graph": "",
        "get_enhanced_dashboard": 'metric_types: str = "all", time_range: str = "24h"',
        "get_time_series_data": 'metric: str, time_range: str = "24h", granularity: str = "hour"',
        "get_correlation_analysis": "metrics: str",
        "get_real_time_activity": "",
        "get_comprehensive_analytics_report": 'time_range: str = "24h", include_predictions: bool = True, include_recommendations: bool = True',
        "get_system_health_analysis": 'time_range: str = "24h"',
        "get_analytics_insights": 'time_range: str = "24h", priority: str = "all"',
        "get_anomaly_detection": 'time_range: str = "24h"',
        "get_usage_pattern_analysis": 'time_range: str = "24h"',
        "create_entity": "entity_data: dict",
        "create_relationship": "relationship_data: dict",
        "get_entity": "entity_id: str",
        "get_entity_relationships": "entity_id: str",
        "search_entities": "q: str, entity_types: str = None, limit: int = 50",
        "get_graph_visualization": "center_entity_id: str = None, max_nodes: int = 100",
        "process_document_entities": "document_data: dict",
        "get_graph_statistics": "",
        "get_entity_insights": "entity_id: str",
        "add_documents_to_semantic_index": "documents: dict",
        "semantic_search": "q: str, top_k: int = 10, min_score: float = 0.5",
        "find_similar_documents": "document_id: str, top_k: int = 5",
        "get_semantic_analytics": "",
        "cluster_documents": "num_clusters: int = 5",
        "extract_entities_from_text": "text_data: dict",
        "analyze_text_content": "text_data: dict",
        "health_check": "",
        "dashboard": "",
        "realtime_dashboard": "",
        "advanced_analytics_dashboard": "",
        "enhanced_obsidian_dashboard": "",
        "obsidian_sync": "request: dict",
        "auto_tag_content": "request: dict",
        "extract_metadata": "request: dict",
        "update_knowledge_graph": "request: dict",
    }

    # Fix function signatures
    for func_name, params in endpoint_fixes.items():
        # Pattern to match function definition with incorrect self parameter
        pattern = rf"(async def {func_name}\()self\) -> None:"

        if params:
            replacement = f"async def {func_name}({params}) -> None:"
        else:
            replacement = f"async def {func_name}() -> None:"

        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            fixes_applied += 1
            print(f"Fixed function signature: {func_name}")

    # Add missing imports for Pydantic models
    if fixes_applied > 0:
        # Add SearchRequest and SummarizeRequest models if not present
        if "class SearchRequest" not in content:
            search_request_model = """
class SearchRequest(BaseModel):
    query: str
    sources: List[str] = ["web", "arxiv", "pubmed"]
    max_results: int = 10
    enable_ml_enhancement: bool = True
    enable_content_summarization: bool = True

"""
            # Insert after existing BaseModel classes
            if "class " in content:
                # Find the last class definition and insert after it
                last_class_match = list(
                    re.finditer(r"class \w+\(BaseModel\):", content)
                )[-1]
                insert_pos = last_class_match.end()
                content = (
                    content[:insert_pos] + search_request_model + content[insert_pos:]
                )
            else:
                # Insert after imports
                import_end = content.find("\n\n")
                content = (
                    content[:import_end] + search_request_model + content[import_end:]
                )

        if "class SummarizeRequest" not in content:
            summarize_request_model = """
class SummarizeRequest(BaseModel):
    content: str
    content_type: str = "text"
    target_sentences: int = 3
    include_key_points: bool = True

"""
            # Insert after SearchRequest
            search_request_pos = content.find("class SearchRequest")
            if search_request_pos != -1:
                insert_pos = content.find("\n\n", search_request_pos)
                content = (
                    content[:insert_pos]
                    + summarize_request_model
                    + content[insert_pos:]
                )

    # Write the fixed content back
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True, fixes_applied

    return False, 0


def main():
    """Fix F821 errors in mcp_server_standalone.py."""
    file_path = Path("mcp_server_standalone.py")

    if not file_path.exists():
        print(f"Error: {file_path} not found")
        return

    print("🔧 Fixing F821 errors in mcp_server_standalone.py...")
    print("=" * 60)

    was_modified, num_fixes = fix_fastapi_endpoints(file_path)

    if was_modified:
        print(f"✅ Fixed {num_fixes} function signatures")
        print("✅ Added missing Pydantic models")
        print("✅ Removed incorrect 'self' parameters")
    else:
        print("ℹ️  No fixes needed")

    print("=" * 60)


if __name__ == "__main__":
    main()
