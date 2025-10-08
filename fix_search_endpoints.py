#!/usr/bin/env python3
"""Fix F821 errors in search_endpoints.py."""

import re


def fix_search_endpoints():
    """Fix F821 errors in search_endpoints.py."""
    file_path = "/home/chris/PAKE_SYSTEM_claude_optimized/src/api/enterprise/search_endpoints.py"

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Fix function signatures based on the F821 errors found
    fixes = [
        # get_search_history function - add dal parameter
        (
            r"async def get_search_history\(\n    limit: int = 50,\n    offset: int = 0,\n    user_filter: str \| None = None,\n    current_user: dict = Depends\(get_current_user\),\n\):",
            "async def get_search_history(\n    dal: Any = Depends(get_dal),\n    limit: int = 50,\n    offset: int = 0,\n    user_filter: str | None = None,\n    current_user: dict = Depends(get_current_user),\n):",
        ),
        # get_search_analytics function - add dal parameter
        (
            r'async def get_search_analytics\(\n    time_range: str = "24h",\n    current_user: dict = Depends\(get_current_user\),\n\):',
            'async def get_search_analytics(\n    dal: Any = Depends(get_dal),\n    time_range: str = "24h",\n    current_user: dict = Depends(get_current_user),\n):',
        ),
        # get_popular_searches function - add dal parameter
        (
            r"async def get_popular_searches\(\n    limit: int = 20,\n    current_user: dict = Depends\(get_current_user\),\n\):",
            "async def get_popular_searches(\n    dal: Any = Depends(get_dal),\n    limit: int = 20,\n    current_user: dict = Depends(get_current_user),\n):",
        ),
        # save_search function - add dal parameter
        (
            r"async def save_search\(\n    search_data: dict,\n    current_user: dict = Depends\(get_current_user\),\n\):",
            "async def save_search(\n    search_data: dict,\n    dal: Any = Depends(get_dal),\n    current_user: dict = Depends(get_current_user),\n):",
        ),
        # get_saved_searches function - add dal parameter
        (
            r"async def get_saved_searches\(\n    current_user: dict = Depends\(get_current_user\),\n\):",
            "async def get_saved_searches(\n    dal: Any = Depends(get_dal),\n    current_user: dict = Depends(get_current_user),\n):",
        ),
        # quick_search function - add missing parameters
        (
            r"async def quick_search\(\n    query: str,\n    current_user: dict = Depends\(get_current_user\),\n\):",
            "async def quick_search(\n    query: str,\n    dal: Any = Depends(get_dal),\n    security_enforcer: Any = Depends(get_security_enforcer),\n    current_user: dict = Depends(get_current_user),\n):",
        ),
        # process_search_results function - add missing parameters
        (
            r"async def process_search_results\(\n    results: List\[dict\],\n    query: str,\n    tenant_id: str,\n\):",
            "async def process_search_results(\n    results: List[dict],\n    query: str,\n    tenant_id: str,\n    dal: Any = Depends(get_dal),\n):",
        ),
        # save_search_history function - add missing parameters
        (
            r"async def save_search_history\(self\) -> None:",
            "async def save_search_history(\n    self,\n    dal: Any = Depends(get_dal),\n    tenant_id: str = Depends(get_current_tenant_id),\n    user_id: str = Depends(get_current_user_id),\n    results_count: int = 0,\n    execution_time_ms: float = 0.0,\n) -> None:",
        ),
    ]

    # Apply fixes
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # Add missing imports at the top
    if "get_dal" not in content:
        # Add import for get_dal
        content = content.replace(
            "from src.security.tenant_isolation_enforcer import enforce_tenant_isolation",
            "from src.security.tenant_isolation_enforcer import enforce_tenant_isolation\nfrom src.services.database.tenant_aware_dal import get_dal\nfrom src.security.tenant_isolation_enforcer import get_security_enforcer",
        )

    # Write back
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Fixed search_endpoints.py")


if __name__ == "__main__":
    fix_search_endpoints()
